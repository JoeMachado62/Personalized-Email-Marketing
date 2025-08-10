"""
Enhanced web scraper using Selenium and MCP Fetch for all operations.
NO PLAYWRIGHT - uses Selenium for search and MCP Fetch for content extraction.
"""

import asyncio
import logging
import re
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse, quote_plus

logger = logging.getLogger(__name__)

# Import Selenium search
from .search_with_selenium import search_with_real_chrome

# Import MCP client for content fetching
from .mcp_client import create_mcp_manager, MCPRouter


class SeleniumWebGatherer:
    """
    Web data gatherer using Selenium for search and MCP Fetch for content extraction.
    No Playwright dependencies - works reliably on Windows.
    """
    
    def __init__(self):
        self.mcp_manager = None
        self.mcp_router = None
        
    async def __aenter__(self):
        """Async context manager entry - initialize MCP"""
        try:
            self.mcp_manager = await create_mcp_manager()
            if self.mcp_manager.initialized:
                self.mcp_router = MCPRouter(self.mcp_manager)
                logger.info("MCP Fetch initialized for content extraction")
            else:
                logger.warning("MCP Fetch not available - will use Selenium fallback")
        except Exception as e:
            logger.warning(f"MCP initialization failed: {e}")
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup"""
        if self.mcp_manager:
            await self.mcp_manager.close()
    
    async def search_and_gather(self, company_name: str, location: str, 
                                additional_data: Dict[str, str] = None,
                                campaign_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Main method: Search for company, scrape sources, return enriched data.
        Uses Selenium for search and MCP Fetch for content extraction.
        
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
            # Step 1: Search using Selenium (synchronous call wrapped in async)
            query = f"{company_name} {location}"
            logger.info(f"Searching with Selenium for: {query}")
            
            # Run Selenium search in executor to make it async-compatible
            loop = asyncio.get_event_loop()
            search_results = await loop.run_in_executor(
                None, 
                search_with_real_chrome, 
                query, 
                False  # headless=False for better results
            )
            
            if search_results:
                gathered_data['search_results'] = search_results
                gathered_data['search_engine'] = 'selenium_chrome'
                logger.info(f"Found {len(search_results)} results using Selenium")
                
                # Step 2: Extract website URL from search results
                website_url = self._identify_official_website(search_results, company_name)
                if website_url:
                    gathered_data['website_url'] = website_url
                    logger.info(f"Identified website: {website_url}")
                    
                    # Step 3: Fetch website content using MCP or fallback
                    website_content = await self._fetch_website_content(website_url)
                    if website_content:
                        gathered_data['website_data'] = website_content
                
                # Step 4: Process additional sources if campaign context provided
                if campaign_context:
                    await self._enrich_with_campaign_context(
                        gathered_data, 
                        search_results, 
                        campaign_context
                    )
            else:
                logger.warning(f"No search results found for {company_name}")
                gathered_data['error'] = "No search results found"
                
        except Exception as e:
            logger.error(f"Error in search_and_gather: {str(e)}")
            gathered_data['error'] = str(e)
            
        return gathered_data
    
    async def _fetch_website_content(self, url: str) -> Dict[str, Any]:
        """
        Fetch website content using MCP Fetch or Selenium fallback.
        
        Args:
            url: Website URL to fetch
            
        Returns:
            Website content and metadata
        """
        try:
            # Try MCP Fetch first (FREE - no token costs)
            if self.mcp_router:
                logger.info(f"Fetching {url} with MCP Fetch")
                content = await self.mcp_router.route(url, content_type='corporate')
                return content
            else:
                # Fallback to Selenium content extraction
                logger.info(f"Using Selenium fallback for {url}")
                return await self._selenium_fetch_fallback(url)
                
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return {'error': str(e), 'url': url}
    
    async def _selenium_fetch_fallback(self, url: str) -> Dict[str, Any]:
        """
        Fallback content fetching using Selenium.
        
        Args:
            url: URL to fetch
            
        Returns:
            Basic content from the page
        """
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        driver = None
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            
            driver.get(url)
            await asyncio.sleep(2)  # Wait for page load
            
            # Extract basic content
            content = {
                'url': url,
                'title': driver.title,
                'text': driver.find_element(By.TAG_NAME, 'body').text[:5000],
                'fetched_via': 'selenium_fallback'
            }
            
            # Try to find contact info
            page_text = content['text'].lower()
            phone_matches = re.findall(r'[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]', page_text)
            email_matches = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', page_text)
            
            if phone_matches:
                content['phones_found'] = list(set(phone_matches[:3]))
            if email_matches:
                content['emails_found'] = list(set(email_matches[:3]))
                
            return content
            
        except Exception as e:
            logger.error(f"Selenium fallback error: {e}")
            return {'error': str(e), 'url': url}
        finally:
            if driver:
                driver.quit()
    
    def _identify_official_website(self, search_results: List[Dict], company_name: str) -> Optional[str]:
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
            if result.get('source') == 'google_my_business' and result.get('website'):
                return result['website']
        
        # Priority 2: First result with company name in domain
        company_words = company_name.lower().split()
        for result in search_results:
            url = result.get('url', '')
            domain = urlparse(url).netloc.lower()
            if any(word in domain for word in company_words if len(word) > 3):
                return url
        
        # Priority 3: First non-directory result
        for result in search_results:
            url = result.get('url', '')
            if not any(dir_site in url for dir_site in ['yelp.', 'yellowpages.', 'facebook.', 'linkedin.']):
                return url
                
        # Fallback: First result
        return search_results[0].get('url') if search_results else None
    
    async def _enrich_with_campaign_context(self, gathered_data: Dict, search_results: List[Dict], 
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
            
            for result in search_results[:5]:  # Process top 5 results
                url = result.get('url', '')
                
                # Prioritize based on campaign needs
                if campaign_context.get('social_focus') and any(
                    social in url for social in ['facebook.', 'linkedin.', 'instagram.']
                ):
                    relevant_sources.append(result)
                elif campaign_context.get('review_focus') and any(
                    review in url for review in ['yelp.', 'google.com/maps', 'trustpilot.']
                ):
                    relevant_sources.append(result)
                elif campaign_context.get('news_focus') and any(
                    news in url for news in ['news', 'press', 'article', 'blog']
                ):
                    relevant_sources.append(result)
            
            # Fetch content from relevant sources
            for source in relevant_sources[:3]:  # Limit to 3 additional sources
                try:
                    content = await self._fetch_website_content(source['url'])
                    source_type = self._identify_source_type(source['url'])
                    gathered_data[f'{source_type}_data'] = content
                except Exception as e:
                    logger.error(f"Error fetching {source['url']}: {e}")
            
            # Generate personalization hooks based on gathered data
            gathered_data['personalization_hooks'] = self._generate_personalization_hooks(
                gathered_data, 
                campaign_context
            )
            
        except Exception as e:
            logger.error(f"Error in campaign enrichment: {e}")
    
    def _identify_source_type(self, url: str) -> str:
        """Identify the type of source from URL"""
        domain = urlparse(url).netloc.lower()
        
        if 'facebook.' in domain:
            return 'facebook'
        elif 'linkedin.' in domain:
            return 'linkedin'
        elif 'yelp.' in domain:
            return 'yelp_reviews'
        elif 'news' in domain or 'press' in url:
            return 'news'
        else:
            return 'other'
    
    def _generate_personalization_hooks(self, data: Dict, context: Dict) -> List[str]:
        """Generate personalization hooks from gathered data"""
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
        if 'yelp_reviews' in data:
            hooks.append("Strong online reputation")
        
        return hooks[:5]  # Limit to 5 hooks


# Backward compatibility - use the new Selenium-based gatherer
WebDataGatherer = SeleniumWebGatherer


# Main search function for backward compatibility
async def search_web(query: str) -> dict:
    """
    Search the web using Selenium.
    
    Args:
        query: Search query
        
    Returns:
        Search results dictionary
    """
    try:
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, search_with_real_chrome, query, False)
        return {
            'query': query,
            'results': results,
            'engine_used': 'selenium_chrome',
            'engines_tried': ['selenium_chrome'],
            'success': len(results) > 0,
            'error': None if results else 'No results found'
        }
    except Exception as e:
        logger.error(f"Search error: {e}")
        return {
            'query': query,
            'results': [],
            'engine_used': 'selenium_chrome',
            'engines_tried': ['selenium_chrome'],
            'success': False,
            'error': str(e)
        }