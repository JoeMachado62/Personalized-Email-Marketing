"""
Web scraper using Playwright with anti-detection and MCP integration.
Replaces web_scraper_selenium.py with better performance and stealth.
"""

import asyncio
import sys
import logging
import re
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse, quote_plus

# Fix Windows event loop for Playwright compatibility
if sys.platform == 'win32':
    try:
        # Check if we're in an existing event loop
        loop = asyncio.get_running_loop()
        # If we're here, we're in an existing loop - can't change policy
        logging.warning("Running in existing event loop - Playwright may have issues on Windows")
    except RuntimeError:
        # No event loop running - safe to set policy
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from .playwright_browser_manager import (
    browser_manager,
    HumanBehaviorSimulator,
    detect_honeypots
)
from .search_with_playwright import PlaywrightSearch

# MCP has been removed - using Playwright-only mode
MCP_AVAILABLE = False

logger = logging.getLogger(__name__)


class PlaywrightWebGatherer:
    """
    Web data gatherer using Playwright for all operations.
    Single browser instance with anti-detection for reliable scraping.
    """
    
    def __init__(self, headless: bool = True):
        """
        Initialize Playwright web gatherer.
        
        Args:
            headless: MUST be True in production to prevent window spam
        """
        self.headless = headless
        self.searcher = PlaywrightSearch(headless=headless)
        self.simulator = HumanBehaviorSimulator()
    
    async def __aenter__(self):
        """Async context manager entry - initialize resources."""
        # Initialize browser manager
        await browser_manager.initialize(headless=self.headless)
        
        # Using Playwright for all operations
        logger.info("Using Playwright for all web operations")
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup resources."""
        # Note: Don't cleanup browser_manager here as it's a singleton
        # It should be cleaned up at application shutdown
        pass
    
    async def search_and_gather(self, company_name: str, location: str,
                               additional_data: Dict[str, str] = None,
                               campaign_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Main method: Search for company, scrape sources, return enriched data.
        Uses Playwright for everything with anti-detection measures.
        
        Args:
            company_name: Name of the business
            location: City/address of the business
            additional_data: Any additional known data (phone, email, etc.)
            campaign_context: Campaign goals and targeting info
            
        Returns:
            Dictionary of enriched profile data
        """
        gathered_data = {
            'company_name': company_name,
            'location': location,
            'search_results': [],
            'website_data': {},
            'social_profiles': {},
            'business_info': {},
            'raw_text_snippets': [],
            'additional_data': additional_data or {},
            'multi_source_profile': {},
            'personalization_hooks': []
        }
        
        try:
            # Step 1: Search using Playwright with anti-detection
            query = f"{company_name} {location}"
            logger.info(f"Searching with Playwright for: {query}")
            
            # Try Google first, fallback to DuckDuckGo if needed
            search_results = await self.searcher.search_google(query, max_results=10)
            
            if not search_results:
                logger.info("Google returned no results, trying DuckDuckGo")
                search_results = await self.searcher.search_duckduckgo(query, max_results=10)
            
            if search_results:
                gathered_data['search_results'] = search_results
                gathered_data['search_engine'] = search_results[0].get('source', 'playwright')
                logger.info(f"Found {len(search_results)} results using Playwright")
                
                # Step 2: Extract website URL from search results
                website_url = self._identify_official_website(search_results, company_name)
                if website_url:
                    gathered_data['website_url'] = website_url
                    logger.info(f"Identified website: {website_url}")
                    
                    # Step 3: Scrape website content
                    website_content = await self._scrape_website(website_url)
                    if website_content:
                        gathered_data['website_data'] = website_content
                
                # Step 4: Process additional sources based on campaign context
                if campaign_context:
                    await self._enrich_with_campaign_context(
                        gathered_data,
                        search_results,
                        campaign_context
                    )
                
                # Step 5: Extract contact information from all gathered data
                gathered_data['extracted_contacts'] = self._extract_contact_info(gathered_data)
                
            else:
                logger.warning(f"No search results found for {company_name}")
                gathered_data['error'] = "No search results found"
                
        except Exception as e:
            logger.error(f"Error in search_and_gather: {str(e)}", exc_info=True)
            gathered_data['error'] = str(e)
        
        return gathered_data
    
    async def _scrape_website(self, url: str) -> Dict[str, Any]:
        """
        Scrape website content using Playwright with anti-detection.
        Falls back to MCP if available for HTML to Markdown conversion.
        
        Args:
            url: Website URL to scrape
            
        Returns:
            Website content and metadata
        """
        context_id = f"scrape_{hash(url)}"
        
        try:
            # Use MCP for content extraction if available (FREE - no token costs)
            if self.mcp_router:
                logger.info(f"Using MCP Fetch for {url}")
                content = await self.mcp_router.route(url, content_type='corporate')
                return content
            
            # Fallback to Playwright scraping
            logger.info(f"Scraping {url} with Playwright")
            
            async with browser_manager.get_page_context(context_id) as page:
                # Navigate with stealth
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                
                # Wait for content to load
                await self.simulator.random_delay(1, 2)
                
                # Detect and avoid honeypots
                honeypots = await detect_honeypots(page)
                if honeypots:
                    logger.info(f"Detected {len(honeypots)} honeypot elements to avoid")
                
                # Simulate human behavior
                await self.simulator.simulate_reading(page, duration_seconds=3)
                
                # Extract content
                content_data = await page.evaluate("""
                    () => {
                        const data = {
                            title: document.title,
                            description: '',
                            text: '',
                            links: [],
                            images: [],
                            contact: {}
                        };
                        
                        // Get meta description
                        const metaDesc = document.querySelector('meta[name="description"]');
                        if (metaDesc) {
                            data.description = metaDesc.content;
                        }
                        
                        // Get main text content
                        const mainContent = document.querySelector('main') || 
                                          document.querySelector('article') || 
                                          document.querySelector('body');
                        if (mainContent) {
                            data.text = mainContent.innerText.substring(0, 10000);
                        }
                        
                        // Extract links
                        const links = document.querySelectorAll('a[href]');
                        const uniqueLinks = new Set();
                        links.forEach(link => {
                            const href = link.href;
                            if (href && !href.startsWith('javascript:')) {
                                uniqueLinks.add(href);
                            }
                        });
                        data.links = Array.from(uniqueLinks).slice(0, 50);
                        
                        // Extract images
                        const images = document.querySelectorAll('img[src]');
                        const uniqueImages = new Set();
                        images.forEach(img => {
                            if (img.src) {
                                uniqueImages.add(img.src);
                            }
                        });
                        data.images = Array.from(uniqueImages).slice(0, 20);
                        
                        // Look for contact information
                        const pageText = document.body.innerText.toLowerCase();
                        
                        // Phone numbers
                        const phoneRegex = /[\\+\\(]?[1-9][0-9 .\\-\\(\\)]{8,}[0-9]/g;
                        const phones = pageText.match(phoneRegex);
                        if (phones) {
                            data.contact.phones = [...new Set(phones.slice(0, 5))];
                        }
                        
                        // Email addresses
                        const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}/g;
                        const emails = pageText.match(emailRegex);
                        if (emails) {
                            data.contact.emails = [...new Set(emails.slice(0, 5))];
                        }
                        
                        // Social media links
                        const socialLinks = {
                            facebook: [],
                            linkedin: [],
                            twitter: [],
                            instagram: []
                        };
                        
                        links.forEach(link => {
                            const href = link.href.toLowerCase();
                            if (href.includes('facebook.com')) {
                                socialLinks.facebook.push(link.href);
                            } else if (href.includes('linkedin.com')) {
                                socialLinks.linkedin.push(link.href);
                            } else if (href.includes('twitter.com') || href.includes('x.com')) {
                                socialLinks.twitter.push(link.href);
                            } else if (href.includes('instagram.com')) {
                                socialLinks.instagram.push(link.href);
                            }
                        });
                        
                        data.contact.social = socialLinks;
                        
                        return data;
                    }
                """)
                
                # Clean up phone numbers
                if content_data.get('contact', {}).get('phones'):
                    cleaned_phones = []
                    for phone in content_data['contact']['phones']:
                        # Basic cleaning
                        cleaned = re.sub(r'[^\d+()-.\s]', '', phone)
                        if len(cleaned) >= 10:  # Valid phone length
                            cleaned_phones.append(cleaned)
                    content_data['contact']['phones'] = cleaned_phones[:3]
                
                # Add metadata
                content_data['url'] = url
                content_data['fetched_via'] = 'playwright'
                content_data['domain'] = urlparse(url).netloc
                
                return content_data
                
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return {
                'error': str(e),
                'url': url,
                'fetched_via': 'playwright_error'
            }
    
    def _identify_official_website(self, search_results: List[Dict], 
                                  company_name: str) -> Optional[str]:
        """
        Identify the most likely official website from search results.
        
        Args:
            search_results: List of search results
            company_name: Company name to match
            
        Returns:
            Most likely official website URL
        """
        if not search_results:
            return None
        
        # Priority 1: Google My Business website
        for result in search_results:
            if result.get('is_gmb') and result.get('url'):
                url = result['url']
                if not url.startswith('https://www.google.com'):
                    return url
        
        # Priority 2: First result with company name in domain
        company_words = [w.lower() for w in company_name.split() if len(w) > 3]
        for result in search_results:
            url = result.get('url', '')
            domain = urlparse(url).netloc.lower()
            if any(word in domain for word in company_words):
                return url
        
        # Priority 3: First non-directory result
        directories = [
            'yelp.', 'yellowpages.', 'facebook.', 'linkedin.',
            'twitter.', 'instagram.', 'bbb.org', 'manta.com',
            'bizapedia.', 'dnb.com', 'zoominfo.'
        ]
        
        for result in search_results:
            url = result.get('url', '')
            domain = urlparse(url).netloc.lower()
            if not any(dir_site in domain for dir_site in directories):
                return url
        
        # Fallback: First result that's not Google
        for result in search_results:
            url = result.get('url', '')
            if url and not url.startswith('https://www.google.com'):
                return url
        
        return None
    
    async def _enrich_with_campaign_context(self, gathered_data: Dict,
                                           search_results: List[Dict],
                                           campaign_context: Dict) -> None:
        """
        Enrich data based on campaign context and goals.
        
        Args:
            gathered_data: Data dictionary to enrich
            search_results: Search results to process
            campaign_context: Campaign targeting information
        """
        try:
            # Select relevant sources based on campaign
            relevant_sources = []
            
            for result in search_results[:7]:  # Process top 7 results
                url = result.get('url', '')
                domain = urlparse(url).netloc.lower()
                
                # Prioritize based on campaign needs
                if campaign_context.get('social_focus'):
                    if any(social in domain for social in 
                          ['facebook.', 'linkedin.', 'instagram.', 'twitter.', 'x.com']):
                        relevant_sources.append(result)
                
                if campaign_context.get('review_focus'):
                    if any(review in domain for review in 
                          ['yelp.', 'google.com/maps', 'trustpilot.', 'bbb.org']):
                        relevant_sources.append(result)
                
                if campaign_context.get('news_focus'):
                    if any(news in url.lower() for news in 
                          ['news', 'press', 'article', 'blog', 'announcement']):
                        relevant_sources.append(result)
            
            # Scrape relevant sources (limit to 3 for performance)
            for source in relevant_sources[:3]:
                try:
                    url = source['url']
                    logger.info(f"Enriching from: {url}")
                    
                    content = await self._scrape_website(url)
                    if content and not content.get('error'):
                        source_type = self._identify_source_type(url)
                        gathered_data[f'{source_type}_data'] = content
                        
                        # Extract specific information based on source type
                        if source_type == 'linkedin' and 'text' in content:
                            gathered_data['linkedin_profile'] = url
                            
                        elif source_type == 'facebook' and 'text' in content:
                            gathered_data['facebook_page'] = url
                            
                except Exception as e:
                    logger.error(f"Error enriching from {source.get('url')}: {e}")
            
            # Generate personalization hooks
            gathered_data['personalization_hooks'] = self._generate_personalization_hooks(
                gathered_data,
                campaign_context
            )
            
        except Exception as e:
            logger.error(f"Error in campaign enrichment: {e}")
    
    def _identify_source_type(self, url: str) -> str:
        """Identify the type of source from URL."""
        domain = urlparse(url).netloc.lower()
        
        if 'facebook.' in domain:
            return 'facebook'
        elif 'linkedin.' in domain:
            return 'linkedin'
        elif 'instagram.' in domain:
            return 'instagram'
        elif 'twitter.' in domain or 'x.com' in domain:
            return 'twitter'
        elif 'yelp.' in domain:
            return 'yelp_reviews'
        elif 'bbb.org' in domain:
            return 'bbb_profile'
        elif any(news in domain for news in ['news', 'press', 'blog']):
            return 'news'
        else:
            return 'other'
    
    def _extract_contact_info(self, data: Dict) -> Dict[str, Any]:
        """
        Extract and consolidate contact information from all gathered data.
        
        Args:
            data: All gathered data
            
        Returns:
            Consolidated contact information
        """
        contacts = {
            'phones': set(),
            'emails': set(),
            'social_profiles': {},
            'addresses': set()
        }
        
        # Extract from website data
        if data.get('website_data'):
            website_contacts = data['website_data'].get('contact', {})
            
            if website_contacts.get('phones'):
                contacts['phones'].update(website_contacts['phones'])
            
            if website_contacts.get('emails'):
                contacts['emails'].update(website_contacts['emails'])
            
            if website_contacts.get('social'):
                for platform, links in website_contacts['social'].items():
                    if links:
                        contacts['social_profiles'][platform] = links[0]
        
        # Extract from search results
        for result in data.get('search_results', []):
            # Check GMB data
            if result.get('is_gmb'):
                if result.get('phone'):
                    contacts['phones'].add(result['phone'])
                if result.get('address'):
                    contacts['addresses'].add(result['address'])
        
        # Extract from additional enriched sources
        for key in ['facebook_data', 'linkedin_data', 'yelp_reviews_data']:
            if key in data and data[key].get('contact'):
                source_contacts = data[key]['contact']
                if source_contacts.get('phones'):
                    contacts['phones'].update(source_contacts['phones'])
                if source_contacts.get('emails'):
                    contacts['emails'].update(source_contacts['emails'])
        
        # Convert sets to lists
        return {
            'phones': list(contacts['phones'])[:3],
            'emails': list(contacts['emails'])[:3],
            'social_profiles': contacts['social_profiles'],
            'addresses': list(contacts['addresses'])[:2]
        }
    
    def _generate_personalization_hooks(self, data: Dict, context: Dict) -> List[str]:
        """Generate personalization hooks from gathered data."""
        hooks = []
        
        # Location-based hooks
        if data.get('location'):
            hooks.append(f"Local business in {data['location']}")
        
        # Industry-based hooks
        if context.get('industry_keywords'):
            for keyword in context['industry_keywords']:
                if keyword.lower() in str(data).lower():
                    hooks.append(f"Specializes in {keyword}")
        
        # Review-based hooks
        if 'yelp_reviews_data' in data:
            hooks.append("Strong online reputation with customer reviews")
        
        # Social media presence
        social_profiles = data.get('extracted_contacts', {}).get('social_profiles', {})
        if social_profiles:
            platforms = list(social_profiles.keys())
            if platforms:
                hooks.append(f"Active on {', '.join(platforms)}")
        
        # Website-based hooks
        if data.get('website_url'):
            domain = urlparse(data['website_url']).netloc
            if '.com' in domain:
                hooks.append("Established online presence")
        
        return hooks[:5]  # Limit to 5 hooks


# Backward compatibility aliases
WebDataGatherer = PlaywrightWebGatherer
WebScraperPlaywright = PlaywrightWebGatherer
SeleniumWebGatherer = PlaywrightWebGatherer  # Replace Selenium version


# Main search function for backward compatibility
async def search_web(query: str) -> dict:
    """
    Search the web using Playwright with anti-detection.
    
    Args:
        query: Search query
        
    Returns:
        Search results dictionary
    """
    try:
        searcher = PlaywrightSearch(headless=True)
        results = await searcher.search_google(query)
        
        return {
            'query': query,
            'results': results,
            'engine_used': 'playwright_google',
            'engines_tried': ['playwright_google'],
            'success': len(results) > 0,
            'error': None if results else 'No results found'
        }
    except Exception as e:
        logger.error(f"Search error: {e}")
        return {
            'query': query,
            'results': [],
            'engine_used': 'playwright_google',
            'engines_tried': ['playwright_google'],
            'success': False,
            'error': str(e)
        }


if __name__ == "__main__":
    # Test the scraper
    logging.basicConfig(level=logging.INFO)
    
    async def test_scraper():
        async with PlaywrightWebGatherer(headless=True) as gatherer:
            result = await gatherer.search_and_gather(
                company_name="BROADWAY AUTO BROKERS INC",
                location="ALACHUA FL",
                campaign_context={
                    'social_focus': True,
                    'review_focus': True
                }
            )
            
            print("\n=== Gathered Data ===")
            print(f"Company: {result['company_name']}")
            print(f"Location: {result['location']}")
            print(f"Website: {result.get('website_url', 'Not found')}")
            print(f"Search results: {len(result.get('search_results', []))}")
            
            if result.get('extracted_contacts'):
                print("\n=== Extracted Contacts ===")
                contacts = result['extracted_contacts']
                print(f"Phones: {contacts.get('phones', [])}")
                print(f"Emails: {contacts.get('emails', [])}")
                print(f"Social: {contacts.get('social_profiles', {})}")
            
            if result.get('personalization_hooks'):
                print("\n=== Personalization Hooks ===")
                for hook in result['personalization_hooks']:
                    print(f"- {hook}")
        
        # Cleanup browser
        await browser_manager.cleanup()
    
    # Run test
    asyncio.run(test_scraper())