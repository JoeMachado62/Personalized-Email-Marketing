"""
Search implementation using Playwright with anti-detection measures.
Replaces search_with_selenium.py with better performance and stealth.
"""

import asyncio
import logging
import re
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus, urlparse

from .playwright_browser_manager import (
    browser_manager,
    HumanBehaviorSimulator,
    detect_honeypots
)

logger = logging.getLogger(__name__)


class PlaywrightSearch:
    """
    Search engine interface using Playwright with anti-detection.
    Uses a single browser instance with multiple contexts for efficiency.
    """
    
    def __init__(self, headless: bool = True):
        """
        Initialize Playwright search.
        
        Args:
            headless: MUST be True in production to prevent window spam
        """
        self.headless = headless
        self.simulator = HumanBehaviorSimulator()
    
    async def search_google(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search Google with anti-detection measures.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            List of search results with title, url, snippet
        """
        results = []
        context_id = f"search_{id(self)}"
        
        try:
            # Initialize browser if needed
            await browser_manager.initialize(headless=self.headless)
            
            # Get page from browser manager
            async with browser_manager.get_page_context(context_id) as page:
                # Navigate to Google
                logger.info(f"Searching Google for: {query}")
                await page.goto('https://www.google.com', wait_until='networkidle')
                
                # Wait a bit and move mouse naturally
                await self.simulator.random_delay(0.5, 1.5)
                await self.simulator.move_mouse_naturally(page, movements=2)
                
                # Find search box and type query
                search_selectors = [
                    'textarea[name="q"]',
                    'input[name="q"]',
                    'input[type="search"]'
                ]
                
                search_box = None
                for selector in search_selectors:
                    search_box = await page.query_selector(selector)
                    if search_box:
                        break
                
                if not search_box:
                    logger.error("Could not find Google search box")
                    return results
                
                # Type search query with human-like behavior
                await self.simulator.human_type(page, search_selectors[0], query)
                await self.simulator.random_delay(0.3, 0.8)
                
                # Submit search (Enter key or button click)
                submit_methods = [
                    lambda: page.keyboard.press('Enter'),
                    lambda: self.simulator.human_click(page, 'button[type="submit"]'),
                    lambda: self.simulator.human_click(page, 'input[type="submit"]')
                ]
                
                for method in submit_methods:
                    try:
                        await method()
                        break
                    except:
                        continue
                
                # Wait for results to load
                try:
                    await page.wait_for_selector('div.g, div[data-hveid]', timeout=10000)
                except:
                    # Try waiting for any result container
                    await page.wait_for_load_state('domcontentloaded', timeout=10000)
                
                await self.simulator.random_delay(1, 2)
                
                # Extract search results
                results = await self._extract_google_results(page, max_results)
                
                # Check for Google My Business panel
                gmb_result = await self._extract_gmb_panel(page)
                if gmb_result:
                    results.insert(0, gmb_result)
                
                logger.info(f"Google search completed: {len(results)} results found")
                
        except Exception as e:
            logger.error(f"Google search error: {str(e)}", exc_info=True)
        
        return results
    
    async def _extract_google_results(self, page, max_results: int) -> List[Dict[str, Any]]:
        """Extract search results from Google results page."""
        results = []
        
        try:
            # Multiple selectors for different Google layouts
            result_selectors = [
                'div.g',  # Standard result container
                'div[data-hveid]',  # Alternative result container
                'div[jscontroller][data-hveid]'  # Another variant
            ]
            
            search_results = []
            for selector in result_selectors:
                elements = await page.query_selector_all(selector)
                if elements:
                    search_results = elements
                    logger.debug(f"Found {len(elements)} results using selector: {selector}")
                    break
            
            # Process each result
            for i, result in enumerate(search_results[:max_results]):
                if i >= max_results:
                    break
                
                try:
                    # Extract data using JavaScript for reliability
                    result_data = await result.evaluate("""
                        (element) => {
                            // Find title (h3 or similar)
                            const titleElem = element.querySelector('h3');
                            const title = titleElem ? titleElem.innerText : '';
                            
                            // Find link
                            const linkElem = element.querySelector('a[href]');
                            const url = linkElem ? linkElem.href : '';
                            
                            // Find snippet
                            let snippet = '';
                            const snippetSelectors = [
                                'span.aCOpRe',
                                'div.VwiC3b',
                                'div.IsZvec',
                                'span[style*="-webkit-line-clamp"]'
                            ];
                            
                            for (const selector of snippetSelectors) {
                                const snippetElem = element.querySelector(selector);
                                if (snippetElem) {
                                    snippet = snippetElem.innerText;
                                    break;
                                }
                            }
                            
                            // If no snippet found, try to get any text content
                            if (!snippet) {
                                const textElems = element.querySelectorAll('span, div');
                                for (const elem of textElems) {
                                    const text = elem.innerText;
                                    if (text && text.length > 50 && text.length < 500) {
                                        snippet = text;
                                        break;
                                    }
                                }
                            }
                            
                            return { title, url, snippet };
                        }
                    """)
                    
                    # Filter out invalid results
                    if (result_data['title'] and 
                        result_data['url'] and 
                        not result_data['url'].startswith('https://www.google.com') and
                        not result_data['url'].startswith('javascript:')):
                        
                        results.append({
                            'title': result_data['title'],
                            'url': result_data['url'],
                            'snippet': result_data['snippet'][:300] if result_data['snippet'] else '',
                            'source': 'google_playwright',
                            'position': i + 1
                        })
                        logger.debug(f"Extracted result #{i+1}: {result_data['title'][:50]}...")
                        
                except Exception as e:
                    logger.debug(f"Error extracting result #{i+1}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error extracting search results: {e}")
        
        return results
    
    async def _extract_gmb_panel(self, page) -> Optional[Dict[str, Any]]:
        """Extract Google My Business panel if present."""
        try:
            # Check for GMB panel
            gmb_selectors = [
                'div[data-attrid*="kc:/local"]',
                'div[jscontroller][data-local-attribute]',
                'div.kp-header'
            ]
            
            gmb_panel = None
            for selector in gmb_selectors:
                gmb_panel = await page.query_selector(selector)
                if gmb_panel:
                    break
            
            if not gmb_panel:
                return None
            
            # Extract GMB data
            gmb_data = await page.evaluate("""
                () => {
                    const data = {};
                    
                    // Business name
                    const nameSelectors = [
                        'h2[data-attrid="title"]',
                        'div[data-attrid="title"] span',
                        'h2.qrShPb'
                    ];
                    for (const selector of nameSelectors) {
                        const elem = document.querySelector(selector);
                        if (elem) {
                            data.name = elem.innerText;
                            break;
                        }
                    }
                    
                    // Website
                    const websiteSelectors = [
                        'a[data-attrid*="website"]',
                        'a[href][data-tooltip*="Website"]'
                    ];
                    for (const selector of websiteSelectors) {
                        const elem = document.querySelector(selector);
                        if (elem) {
                            data.website = elem.href;
                            break;
                        }
                    }
                    
                    // Phone
                    const phoneSelectors = [
                        'span[data-attrid*="phone"]',
                        'a[href^="tel:"]',
                        'span[aria-label*="Phone"]'
                    ];
                    for (const selector of phoneSelectors) {
                        const elem = document.querySelector(selector);
                        if (elem) {
                            data.phone = elem.innerText || elem.getAttribute('aria-label');
                            break;
                        }
                    }
                    
                    // Address
                    const addressSelectors = [
                        'span[data-attrid*="address"]',
                        'div[data-attrid="kc:/location/location:address"]'
                    ];
                    for (const selector of addressSelectors) {
                        const elem = document.querySelector(selector);
                        if (elem) {
                            data.address = elem.innerText;
                            break;
                        }
                    }
                    
                    // Rating
                    const ratingElem = document.querySelector('span[aria-label*="stars"]');
                    if (ratingElem) {
                        const ratingText = ratingElem.getAttribute('aria-label');
                        const ratingMatch = ratingText.match(/([0-9.]+)/);
                        if (ratingMatch) {
                            data.rating = parseFloat(ratingMatch[1]);
                        }
                    }
                    
                    return data;
                }
            """)
            
            if gmb_data and gmb_data.get('name'):
                return {
                    'title': gmb_data['name'],
                    'url': gmb_data.get('website', f"https://www.google.com/search?q={quote_plus(gmb_data['name'])}"),
                    'snippet': f"Google My Business listing. Phone: {gmb_data.get('phone', 'N/A')}",
                    'source': 'google_my_business',
                    'phone': gmb_data.get('phone'),
                    'address': gmb_data.get('address'),
                    'rating': gmb_data.get('rating'),
                    'is_gmb': True,
                    'position': 0
                }
            
        except Exception as e:
            logger.debug(f"Error extracting GMB panel: {e}")
        
        return None
    
    async def search_duckduckgo(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search DuckDuckGo as a fallback option.
        
        Args:
            query: Search query string
            max_results: Maximum number of results
            
        Returns:
            List of search results
        """
        results = []
        context_id = f"ddg_{id(self)}"
        
        try:
            await browser_manager.initialize(headless=self.headless)
            
            async with browser_manager.get_page_context(context_id) as page:
                # Navigate to DuckDuckGo
                search_url = f"https://duckduckgo.com/?q={quote_plus(query)}"
                logger.info(f"Searching DuckDuckGo for: {query}")
                await page.goto(search_url, wait_until='networkidle')
                
                # Wait for results
                await self.simulator.random_delay(1, 2)
                
                # Extract results
                result_elements = await page.query_selector_all('article[data-testid="result"]')
                
                for i, element in enumerate(result_elements[:max_results]):
                    try:
                        result_data = await element.evaluate("""
                            (element) => {
                                const titleElem = element.querySelector('h2');
                                const linkElem = element.querySelector('a[href]');
                                const snippetElem = element.querySelector('span');
                                
                                return {
                                    title: titleElem ? titleElem.innerText : '',
                                    url: linkElem ? linkElem.href : '',
                                    snippet: snippetElem ? snippetElem.innerText : ''
                                };
                            }
                        """)
                        
                        if result_data['title'] and result_data['url']:
                            results.append({
                                'title': result_data['title'],
                                'url': result_data['url'],
                                'snippet': result_data['snippet'][:300],
                                'source': 'duckduckgo_playwright',
                                'position': i + 1
                            })
                            
                    except Exception as e:
                        logger.debug(f"Error extracting DuckDuckGo result: {e}")
                
                logger.info(f"DuckDuckGo search completed: {len(results)} results")
                
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
        
        return results
    
    async def search_multi_engine(self, query: str, engines: List[str] = None,
                                 max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search multiple engines and combine results.
        
        Args:
            query: Search query
            engines: List of engines to use (default: google, duckduckgo)
            max_results: Maximum results per engine
            
        Returns:
            Combined and deduplicated results
        """
        if engines is None:
            engines = ['google', 'duckduckgo']
        
        all_results = []
        seen_urls = set()
        
        for engine in engines:
            try:
                if engine == 'google':
                    results = await self.search_google(query, max_results)
                elif engine == 'duckduckgo':
                    results = await self.search_duckduckgo(query, max_results)
                else:
                    logger.warning(f"Unknown search engine: {engine}")
                    continue
                
                # Add unique results
                for result in results:
                    url = result.get('url', '')
                    if url and url not in seen_urls:
                        all_results.append(result)
                        seen_urls.add(url)
                        
            except Exception as e:
                logger.error(f"Error searching {engine}: {e}")
        
        return all_results


# Convenience function for backward compatibility
async def search_with_playwright(query: str, headless: bool = True,
                                max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Convenience function to search with Playwright.
    
    Args:
        query: Search query
        headless: Run in headless mode (MUST be True in production)
        max_results: Maximum number of results
        
    Returns:
        List of search results
    """
    searcher = PlaywrightSearch(headless=headless)
    return await searcher.search_google(query, max_results)


# Synchronous wrapper for compatibility with existing code
def search_with_real_chrome(query: str, headless: bool = True) -> List[Dict[str, Any]]:
    """
    Synchronous wrapper for Playwright search (backward compatibility).
    Replaces the Selenium version with same interface.
    
    Args:
        query: Search query
        headless: Run in headless mode
        
    Returns:
        List of search results
    """
    import nest_asyncio
    
    # Allow nested event loops (fixes compatibility issues)
    try:
        nest_asyncio.apply()
    except:
        pass
    
    # Get or create event loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Run async function
    if loop.is_running():
        # If loop is already running, create a task
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, search_with_playwright(query, headless))
            return future.result()
    else:
        # Normal execution
        return loop.run_until_complete(search_with_playwright(query, headless))


if __name__ == "__main__":
    # Test the search
    logging.basicConfig(level=logging.INFO)
    
    async def test_search():
        test_query = "BROADWAY AUTO BROKERS INC ALACHUA FL"
        print(f"Testing Playwright search for: {test_query}")
        
        searcher = PlaywrightSearch(headless=True)  # Always headless
        results = await searcher.search_google(test_query)
        
        print(f"\nFound {len(results)} results:")
        for i, result in enumerate(results[:5], 1):
            print(f"\n{i}. {result['title']}")
            print(f"   URL: {result['url']}")
            print(f"   Snippet: {result['snippet'][:100]}...")
            print(f"   Source: {result['source']}")
        
        # Cleanup
        await browser_manager.cleanup()
    
    # Run test
    asyncio.run(test_search())