"""
Enhanced scraper service that builds upon the existing auto_enrich scraper.

This service provides improved web scraping capabilities with better error handling,
retries, caching integration, and enhanced contact information extraction.
It uses the existing scraper.py as the foundation while adding production-ready features.
"""

import asyncio
import logging
import re
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import random

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from auto_enrich.scraper import find_dealer_website, extract_contact_info
from .cache_service import get_cache_service

logger = logging.getLogger(__name__)


@dataclass
class ScrapingResult:
    """Result of a scraping operation with metadata."""
    success: bool
    website: Optional[str] = None
    contact_info: Optional[Dict[str, Optional[str]]] = None
    error_message: Optional[str] = None
    attempts: int = 1
    processing_time_ms: int = 0
    cached: bool = False
    cost_estimate: float = 0.0


@dataclass
class ScrapingConfig:
    """Configuration for scraping operations."""
    max_retries: int = 3
    retry_delay_base: float = 1.0  # Base delay in seconds
    retry_delay_max: float = 10.0  # Maximum delay in seconds
    timeout_ms: int = 30000
    headless: bool = True
    user_agent: Optional[str] = None
    use_cache: bool = True
    cache_ttl_hours: int = 24
    concurrent_limit: int = 3


class EnhancedScraperService:
    """
    Enhanced scraper service with retry logic, caching, and better error handling.
    
    This service wraps the existing auto_enrich scraper with production-ready features:
    - Intelligent retry with exponential backoff
    - Caching integration to prevent duplicate searches
    - Enhanced contact information extraction
    - Rate limiting and concurrent request management
    - Comprehensive error handling and logging
    """
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        self.config = config or ScrapingConfig()
        self.cache_service = get_cache_service()
        self._semaphore = asyncio.Semaphore(self.config.concurrent_limit)
        self._rate_limiter = asyncio.Semaphore(self.config.concurrent_limit)
        
        # Cost estimates per operation (in USD)
        self.cost_estimates = {
            "website_search": 0.10,  # Estimated cost of a search operation
            "contact_extraction": 0.05  # Estimated cost of contact extraction
        }
    
    async def find_dealer_website_enhanced(self, dealer_name: str, city: str) -> ScrapingResult:
        """
        Enhanced version of dealer website discovery with caching and retries.
        
        Args:
            dealer_name: Name of the dealership
            city: City where the dealership is located
            
        Returns:
            ScrapingResult with website URL and metadata
        """
        start_time = datetime.now()
        
        # Check cache first if enabled
        if self.config.use_cache:
            cached_website = await self.cache_service.get_website_cache(dealer_name, city)
            if cached_website is not None:
                processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
                return ScrapingResult(
                    success=True,
                    website=cached_website,
                    processing_time_ms=processing_time,
                    cached=True,
                    cost_estimate=0.0  # No cost for cached results
                )
        
        # Acquire semaphore for rate limiting
        async with self._semaphore:
            result = await self._find_website_with_retries(dealer_name, city)
            
            # Cache the result if successful and caching is enabled
            if self.config.use_cache and result.success:
                cost_saved = self.cost_estimates["website_search"]
                await self.cache_service.set_website_cache(
                    dealer_name, city, result.website, cost_saved=cost_saved
                )
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            result.processing_time_ms = processing_time
            result.cost_estimate = self.cost_estimates["website_search"]
            
            return result
    
    async def _find_website_with_retries(self, dealer_name: str, city: str) -> ScrapingResult:
        """Find dealer website with retry logic."""
        last_error = None
        
        for attempt in range(1, self.config.max_retries + 1):
            try:
                logger.debug(f"Attempting website search for {dealer_name} in {city} (attempt {attempt})")
                
                # Use the existing scraper function with enhanced error handling
                website = await self._safe_website_search(dealer_name, city)
                
                return ScrapingResult(
                    success=True,
                    website=website,
                    attempts=attempt
                )
                
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Website search attempt {attempt} failed for {dealer_name}: {e}")
                
                if attempt < self.config.max_retries:
                    delay = min(
                        self.config.retry_delay_base * (2 ** (attempt - 1)) + random.uniform(0, 1),
                        self.config.retry_delay_max
                    )
                    await asyncio.sleep(delay)
        
        return ScrapingResult(
            success=False,
            error_message=f"All {self.config.max_retries} attempts failed. Last error: {last_error}",
            attempts=self.config.max_retries
        )
    
    async def _safe_website_search(self, dealer_name: str, city: str) -> Optional[str]:
        """Safely perform website search with enhanced error handling."""
        try:
            # Use the existing find_dealer_website function
            website = await find_dealer_website(dealer_name, city)
            
            # Validate and clean the URL
            if website:
                website = self._clean_and_validate_url(website)
                
            return website
            
        except Exception as e:
            logger.error(f"Error in safe website search: {e}")
            raise
    
    def _clean_and_validate_url(self, url: str) -> Optional[str]:
        """Clean and validate a URL."""
        if not url:
            return None
        
        # Remove any trailing parameters or fragments that might be noise
        url = url.split('#')[0]  # Remove fragment
        
        # Basic URL validation
        if not (url.startswith('http://') or url.startswith('https://')):
            if url.startswith('www.'):
                url = 'https://' + url
            elif '.' in url and not url.startswith('/'):
                url = 'https://' + url
            else:
                return None
        
        # Filter out obviously invalid domains
        invalid_patterns = [
            r'google\.',
            r'facebook\.',
            r'instagram\.',
            r'twitter\.',
            r'linkedin\.',
            r'youtube\.',
            r'yelp\.',
            r'wikipedia\.'
        ]
        
        for pattern in invalid_patterns:
            if re.search(pattern, url.lower()):
                logger.debug(f"Filtered out invalid URL: {url}")
                return None
        
        return url
    
    async def extract_contact_info_enhanced(self, url: str) -> ScrapingResult:
        """
        Enhanced contact information extraction with retries and better parsing.
        
        Args:
            url: Website URL to extract contact info from
            
        Returns:
            ScrapingResult with contact information and metadata
        """
        start_time = datetime.now()
        
        if not url:
            return ScrapingResult(
                success=False,
                error_message="No URL provided for contact extraction"
            )
        
        # Acquire semaphore for rate limiting
        async with self._semaphore:
            result = await self._extract_contact_with_retries(url)
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            result.processing_time_ms = processing_time
            result.cost_estimate = self.cost_estimates["contact_extraction"]
            
            return result
    
    async def _extract_contact_with_retries(self, url: str) -> ScrapingResult:
        """Extract contact info with retry logic."""
        last_error = None
        
        for attempt in range(1, self.config.max_retries + 1):
            try:
                logger.debug(f"Attempting contact extraction from {url} (attempt {attempt})")
                
                contact_info = await self._safe_contact_extraction(url)
                
                return ScrapingResult(
                    success=True,
                    contact_info=contact_info,
                    attempts=attempt
                )
                
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Contact extraction attempt {attempt} failed for {url}: {e}")
                
                if attempt < self.config.max_retries:
                    delay = min(
                        self.config.retry_delay_base * (2 ** (attempt - 1)) + random.uniform(0, 1),
                        self.config.retry_delay_max
                    )
                    await asyncio.sleep(delay)
        
        return ScrapingResult(
            success=False,
            error_message=f"All {self.config.max_retries} attempts failed. Last error: {last_error}",
            attempts=self.config.max_retries
        )
    
    async def _safe_contact_extraction(self, url: str) -> Dict[str, Optional[str]]:
        """Safely extract contact information with enhanced parsing."""
        # Start with the existing extract_contact_info function
        contact_info = await extract_contact_info(url)
        
        # Enhance with additional extraction logic
        enhanced_info = await self._enhanced_contact_parsing(url)
        
        # Merge results, preferring enhanced info if available
        for key, value in enhanced_info.items():
            if value and not contact_info.get(key):
                contact_info[key] = value
        
        return contact_info
    
    async def _enhanced_contact_parsing(self, url: str) -> Dict[str, Optional[str]]:
        """Enhanced contact information parsing using improved patterns."""
        contact_info = {"phone": None, "email": None, "owner_name": None}
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=self.config.headless,
                    timeout=self.config.timeout_ms
                )
                
                context = await browser.new_context()
                
                if self.config.user_agent:
                    await context.set_extra_http_headers({
                        'User-Agent': self.config.user_agent
                    })
                
                page = await context.new_page()
                
                try:
                    await page.goto(url, timeout=self.config.timeout_ms)
                    await page.wait_for_load_state('networkidle', timeout=10000)
                    
                    # Get page content
                    content = await page.content()
                    text = await page.inner_text('body')
                    
                    # Extract phone numbers
                    phone = self._extract_phone_numbers(text)
                    if phone:
                        contact_info["phone"] = phone[0]  # Take first found
                    
                    # Extract email addresses
                    email = self._extract_email_addresses(text)
                    if email:
                        contact_info["email"] = email[0]  # Take first found
                    
                    # Extract owner/manager names
                    owner_name = self._extract_owner_names(text)
                    if owner_name:
                        contact_info["owner_name"] = owner_name
                    
                except Exception as e:
                    logger.warning(f"Error parsing contact info from {url}: {e}")
                
                finally:
                    await browser.close()
                    
        except Exception as e:
            logger.error(f"Error in enhanced contact parsing: {e}")
        
        return contact_info
    
    def _extract_phone_numbers(self, text: str) -> List[str]:
        """Extract phone numbers from text using various patterns."""
        patterns = [
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # XXX-XXX-XXXX or XXX.XXX.XXXX
            r'\(\d{3}\)\s*\d{3}[-.]?\d{4}',    # (XXX) XXX-XXXX
            r'\b\d{3}\s+\d{3}\s+\d{4}\b',      # XXX XXX XXXX
        ]
        
        phones = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            phones.extend(matches)
        
        # Clean and validate phone numbers
        cleaned_phones = []
        for phone in phones:
            cleaned = re.sub(r'[^\d]', '', phone)
            if len(cleaned) == 10:  # Valid US phone number
                cleaned_phones.append(phone)
        
        return cleaned_phones[:3]  # Return at most 3 phone numbers
    
    def _extract_email_addresses(self, text: str) -> List[str]:
        """Extract email addresses from text."""
        pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(pattern, text)
        
        # Filter out common non-business emails
        filtered_emails = []
        for email in emails:
            domain = email.split('@')[1].lower()
            # Skip common generic/social domains
            if not any(skip in domain for skip in ['gmail', 'yahoo', 'hotmail', 'outlook', 'facebook', 'twitter']):
                filtered_emails.append(email)
        
        return filtered_emails[:3]  # Return at most 3 emails
    
    def _extract_owner_names(self, text: str) -> Optional[str]:
        """Extract potential owner/manager names from text."""
        # Look for common patterns indicating ownership/management
        patterns = [
            r'Owner:?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'Manager:?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'President:?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'Founded by\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0]
        
        return None
    
    async def bulk_enrich_websites(self, dealers: List[Tuple[str, str]]) -> List[ScrapingResult]:
        """
        Enrich multiple dealers' websites concurrently.
        
        Args:
            dealers: List of (dealer_name, city) tuples
            
        Returns:
            List of ScrapingResults in the same order as input
        """
        logger.info(f"Starting bulk website enrichment for {len(dealers)} dealers")
        
        # Create tasks for concurrent processing
        tasks = [
            self.find_dealer_website_enhanced(dealer_name, city)
            for dealer_name, city in dealers
        ]
        
        # Execute with concurrency control
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to ScrapingResult objects
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                dealer_name, city = dealers[i]
                processed_results.append(ScrapingResult(
                    success=False,
                    error_message=f"Exception during processing: {str(result)}"
                ))
            else:
                processed_results.append(result)
        
        # Log summary statistics
        successful = sum(1 for r in processed_results if r.success)
        cached = sum(1 for r in processed_results if r.cached)
        total_cost = sum(r.cost_estimate for r in processed_results if not r.cached)
        
        logger.info(f"Bulk enrichment completed: {successful}/{len(dealers)} successful, "
                   f"{cached} cached, estimated cost: ${total_cost:.2f}")
        
        return processed_results
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check of the scraper service."""
        try:
            # Test basic Playwright functionality
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto('https://httpbin.org/status/200', timeout=10000)
                await browser.close()
            
            # Get cache statistics
            cache_stats = self.cache_service.get_stats()
            
            return {
                "status": "healthy",
                "playwright_available": True,
                "cache_stats": cache_stats,
                "config": {
                    "max_retries": self.config.max_retries,
                    "concurrent_limit": self.config.concurrent_limit,
                    "use_cache": self.config.use_cache
                }
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "playwright_available": False
            }


# Global service instance
_scraper_service: Optional[EnhancedScraperService] = None


def get_scraper_service(config: Optional[ScrapingConfig] = None) -> EnhancedScraperService:
    """Get the global scraper service instance."""
    global _scraper_service
    if _scraper_service is None:
        _scraper_service = EnhancedScraperService(config)
    return _scraper_service