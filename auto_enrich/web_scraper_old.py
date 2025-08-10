"""
Enhanced web scraper using Selenium and MCP Fetch.
This follows the architectural design: Search -> Scrape -> AI Interpret -> Store
NO PLAYWRIGHT - uses Selenium for search and MCP Fetch for content extraction.
"""

import asyncio
import logging
import re
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse, quote_plus
import json

logger = logging.getLogger(__name__)

# Import the Selenium-only implementation
try:
    from .web_scraper_selenium import SeleniumWebGatherer, search_web
    logger.info("Using Selenium + MCP Fetch implementation")
except ImportError as e:
    logger.error(f"Failed to import Selenium implementation: {e}")
    raise


# Use the Selenium implementation
WebDataGatherer = SeleniumWebGatherer

# The old Playwright implementation is kept below for reference only
# It is NOT used and may have import errors - this is intentional
"""
class OLD_PLAYWRIGHT_WebDataGatherer:
    """
    Gathers raw data from the web for AI interpretation.
    This reduces costs by only using AI to interpret already-gathered data.
    """
    
    def __init__(self):
        self.browser = None
        self.context = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
    
    async def search_and_gather(self, company_name: str, location: str, 
                                additional_data: Dict[str, str] = None,
                                campaign_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Main method: Search for company, scrape multiple high-value sources, return enriched profile data.
        
        Args:
            company_name: Name of the business
            location: City/address of the business  
            additional_data: Any additional known data (phone, email, etc.)
            campaign_context: Campaign goals and targeting info for personalization
            
        Returns:
            Dictionary of enriched profile data from multiple sources
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
            # Step 1: Multi-engine search with fallback
            query = f"{company_name} {location}"
            logger.info(f"Searching for: {query}")
            
            search_response = await search_web(query)
            
            if search_response['success']:
                gathered_data['search_results'] = search_response['results']
                gathered_data['search_engine'] = search_response['engine_used']
                logger.info(f"Found {len(search_response['results'])} results using {search_response['engine_used']}")
                
                # Step 2: Use ProfileBuilder for intelligent multi-source scraping
                if campaign_context:
                    from .profile_builder import ProfileBuilder
                    
                    builder = ProfileBuilder(campaign_context)
                    
                    # Prioritize search results based on personalization value
                    prioritized_results = builder.prioritize_search_results(
                        search_response['results'], 
                        company_name
                    )
                    
                    # Select best sources to scrape (social media, reviews, news, etc.)
                    selected_sources = builder.select_sources_to_scrape(
                        prioritized_results, 
                        max_sources=5
                    )
                    
                    # Extract data from each selected source
                    multi_source_data = []
                    for source in selected_sources:
                        try:
                            logger.info(f"Scraping {source['source_type']}: {source['url'][:60]}...")
                            source_data = await builder.extract_profile_data(source, self.context)
                            multi_source_data.append(source_data)
                        except Exception as e:
                            logger.error(f"Failed to scrape {source['url']}: {e}")
                    
                    # Synthesize comprehensive profile from all sources
                    profile = builder.synthesize_profile(multi_source_data)
                    gathered_data['multi_source_profile'] = profile
                    gathered_data['personalization_hooks'] = profile.get('personalization_hooks', [])
                    
                    logger.info(f"Built profile from {len(profile['sources_used'])} sources")
                    logger.info(f"Generated {len(profile['personalization_hooks'])} personalization hooks")
                    
                else:
                    # Fallback to single-source scraping if no campaign context
                    logger.info("No campaign context provided, using single-source scraping")
                    website_url = self._identify_official_website(gathered_data.get('search_results', []), company_name)
                    if website_url:
                        logger.info(f"Found likely website: {website_url}")
                        gathered_data['website_url'] = website_url
                        
                        try:
                            website_data = await self._scrape_website(website_url)
                            gathered_data['website_data'] = website_data
                        except Exception as e:
                            logger.error(f"Failed to scrape website {website_url}: {str(e)}")
                            gathered_data['website_scrape_error'] = str(e)
            else:
                # Log detailed failure information
                logger.warning(f"Search failed for '{company_name}' after trying: {', '.join(search_response['engines_tried'])}")
                logger.debug(f"Search error details: {search_response.get('error', 'Unknown error')}")
                gathered_data['search_error'] = search_response.get('error', 'All search engines failed')
                gathered_data['engines_tried'] = search_response['engines_tried']
                
                # Still try to proceed with limited data if we have a company name
                if company_name:
                    gathered_data['search_fallback'] = True
                    logger.info(f"Proceeding with limited data for {company_name}")
            
            # Step 3: Search for additional business info (Google My Business, directories)
            business_info = await self._search_business_info(company_name, location)
            gathered_data['business_info'] = business_info
            
        except Exception as e:
            logger.error(f"Critical error gathering data for {company_name}: {str(e)}", exc_info=True)
            gathered_data['error'] = str(e)
            gathered_data['error_type'] = type(e).__name__
        
        return gathered_data
    
    async def _google_search(self, company_name: str, location: str) -> List[Dict]:
        """
        Perform Google search and extract results WITHOUT using API.
        """
        page = await self.context.new_page()
        results = []
        
        try:
            query = f"{company_name} {location} dealer contact information"
            search_url = f"https://www.google.com/search?q={quote_plus(query)}"
            
            logger.debug(f"Navigating to: {search_url}")
            await page.goto(search_url, wait_until='networkidle')
            
            # Wait for search results
            await page.wait_for_selector('div#search', timeout=10000)
            
            # Extract search result entries
            search_divs = await page.query_selector_all('div.g')
            
            for div in search_divs[:5]:  # Top 5 results
                try:
                    # Get title
                    title_elem = await div.query_selector('h3')
                    title = await title_elem.inner_text() if title_elem else ''
                    
                    # Get URL
                    link_elem = await div.query_selector('a')
                    url = await link_elem.get_attribute('href') if link_elem else ''
                    
                    # Get snippet text
                    snippet_elem = await div.query_selector('span.aCOpRe, div.VwiC3b')
                    snippet = await snippet_elem.inner_text() if snippet_elem else ''
                    
                    if url and title:
                        results.append({
                            'title': title,
                            'url': url,
                            'snippet': snippet,
                            'source': 'google_search'
                        })
                        
                        # Extract any visible contact info from snippet
                        phone_matches = re.findall(r'[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]', snippet)
                        email_matches = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', snippet)
                        
                        if phone_matches:
                            results[-1]['found_phones'] = phone_matches
                        if email_matches:
                            results[-1]['found_emails'] = email_matches
                            
                except Exception as e:
                    logger.debug(f"Error extracting search result: {e}")
                    continue
            
            # Also check for Google My Business panel
            gmb_panel = await page.query_selector('div[data-attrid="kc:/local:one box"]')
            if gmb_panel:
                gmb_data = await self._extract_gmb_panel(page)
                if gmb_data:
                    results.insert(0, gmb_data)  # Put GMB data first
                    
        except Exception as e:
            logger.error(f"Google search error: {str(e)}")
        finally:
            await page.close()
            
        return results
    
    async def _extract_gmb_panel(self, page: Page) -> Optional[Dict]:
        """Extract Google My Business panel information"""
        try:
            gmb_data = {
                'source': 'google_my_business',
                'type': 'business_panel'
            }
            
            # Business name
            name_elem = await page.query_selector('h2[data-attrid="title"]')
            if name_elem:
                gmb_data['business_name'] = await name_elem.inner_text()
            
            # Address
            addr_elem = await page.query_selector('span[data-local-attribute="d3adr"] span.LrzXr')
            if addr_elem:
                gmb_data['address'] = await addr_elem.inner_text()
            
            # Phone
            phone_elem = await page.query_selector('span[data-local-attribute="d3ph"] span.LrzXr')
            if phone_elem:
                gmb_data['phone'] = await phone_elem.inner_text()
            
            # Website
            website_elem = await page.query_selector('a[data-local-attribute="d3web"]')
            if website_elem:
                gmb_data['website'] = await website_elem.get_attribute('href')
            
            # Hours
            hours_elem = await page.query_selector('div.MkV9Lb span.LrzXr')
            if hours_elem:
                gmb_data['hours'] = await hours_elem.inner_text()
                
            return gmb_data if len(gmb_data) > 2 else None
            
        except Exception as e:
            logger.debug(f"Error extracting GMB panel: {e}")
            return None
    
    def _identify_official_website(self, search_results: List[Dict], company_name: str) -> Optional[str]:
        """
        Identify the most likely official website from search results.
        """
        if not search_results:
            return None
            
        # Priority 1: Google My Business website
        for result in search_results:
            if result.get('source') == 'google_my_business' and result.get('website'):
                return result['website']
        
        # Priority 2: URL containing company name
        company_words = company_name.lower().split()
        for result in search_results:
            url = result.get('url', '').lower()
            if url and any(word in url for word in company_words if len(word) > 3):
                # Skip social media and directories
                if not any(skip in url for skip in ['facebook.', 'instagram.', 'yelp.', 'yellowpages.']):
                    return result['url']
        
        # Priority 3: First non-social media result
        for result in search_results:
            url = result.get('url', '')
            if url and not any(skip in url for skip in ['facebook.', 'instagram.', 'yelp.', 'yellowpages.']):
                return url
                
        return None
    
    async def _scrape_website(self, url: str) -> Dict[str, Any]:
        """
        Scrape the website for relevant data.
        """
        page = await self.context.new_page()
        scraped_data = {
            'url': url,
            'title': '',
            'meta_description': '',
            'contact_info': {},
            'about_text': [],
            'key_phrases': []
        }
        
        try:
            logger.info(f"Scraping website: {url}")
            
            # Add retry logic for website scraping
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    await page.goto(url, wait_until='networkidle', timeout=15000)
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"Retry {attempt + 1} for {url}: {str(e)}")
                        await asyncio.sleep(2)  # Wait before retry
                    else:
                        raise
            
            # Get page title
            scraped_data['title'] = await page.title()
            
            # Get meta description
            meta_desc = await page.query_selector('meta[name="description"]')
            if meta_desc:
                scraped_data['meta_description'] = await meta_desc.get_attribute('content')
            
            # Extract all text content
            text_content = await page.inner_text('body')
            
            # Find contact information
            scraped_data['contact_info'] = self._extract_contact_info(text_content)
            
            # Look for About Us content
            about_section = await page.query_selector('section#about, div.about, [class*="about"]')
            if about_section:
                about_text = await about_section.inner_text()
                scraped_data['about_text'] = [about_text[:500]]  # First 500 chars
            
            # Extract key phrases from headers
            headers = await page.query_selector_all('h1, h2, h3')
            key_phrases = []
            for header in headers[:10]:
                text = await header.inner_text()
                if text and len(text) < 100:
                    key_phrases.append(text)
            scraped_data['key_phrases'] = key_phrases
            
            # Check for specific dealer-related content
            inventory_link = await page.query_selector('a[href*="inventory"], a[href*="vehicles"]')
            if inventory_link:
                scraped_data['has_inventory'] = True
                
            # Look for team/staff information
            team_section = await page.query_selector('[class*="team"], [class*="staff"], [id*="team"]')
            if team_section:
                team_text = await team_section.inner_text()
                # Extract potential owner names
                owner_patterns = re.findall(r'(?:owner|president|ceo|founder)[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)', 
                                          team_text, re.IGNORECASE)
                if owner_patterns:
                    scraped_data['potential_owners'] = owner_patterns
                    
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            scraped_data['error'] = str(e)
        finally:
            await page.close()
            
        return scraped_data
    
    def _extract_contact_info(self, text: str) -> Dict[str, List[str]]:
        """
        Extract contact information from text using regex patterns.
        """
        contact_info = {}
        
        # Phone numbers
        phone_pattern = r'(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        phones = re.findall(phone_pattern, text)
        if phones:
            contact_info['phones'] = list(set(phones[:3]))  # Top 3 unique
        
        # Email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            contact_info['emails'] = list(set(emails[:3]))  # Top 3 unique
        
        # Addresses (basic pattern for US addresses)
        address_pattern = r'\d+\s+[\w\s]+(?:street|st|avenue|ave|road|rd|drive|dr|lane|ln|boulevard|blvd)[\w\s,]+\d{5}'
        addresses = re.findall(address_pattern, text, re.IGNORECASE)
        if addresses:
            contact_info['addresses'] = addresses[:2]  # Top 2
            
        return contact_info
    
    async def _search_business_info(self, company_name: str, location: str) -> Dict[str, Any]:
        """
        Search for additional business information from directories.
        """
        # This is a simplified version - could be expanded to check multiple sources
        page = await self.context.new_page()
        business_info = {}
        
        try:
            # Search for business hours, reviews, etc.
            query = f"{company_name} {location} hours reviews"
            search_url = f"https://www.google.com/search?q={quote_plus(query)}"
            
            await page.goto(search_url, wait_until='networkidle')
            
            # Extract any additional structured data
            # This is where you could parse schema.org data, reviews, etc.
            
        except Exception as e:
            logger.debug(f"Error searching business info: {e}")
        finally:
            await page.close()
            
        return business_info


async def gather_web_data(company_name: str, location: str, 
                         additional_data: Dict[str, str] = None,
                         campaign_context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Convenience function to gather web data for a company.
    
    Args:
        company_name: Business name
        location: Business location
        additional_data: Any known data (phone, email, etc.)
        campaign_context: Campaign goals for targeted scraping and personalization
    """
    async with WebDataGatherer() as gatherer:
        return await gatherer.search_and_gather(company_name, location, additional_data, campaign_context)
"""