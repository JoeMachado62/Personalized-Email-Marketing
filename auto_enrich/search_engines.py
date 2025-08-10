"""
Multi-engine search with fallback support.
Uses Google as primary, DuckDuckGo as fallback - both without API keys.
"""

import asyncio
import logging
import re
import random
from typing import Dict, List, Optional, Any
from urllib.parse import quote_plus
import json

logger = logging.getLogger(__name__)


class SearchEngine:
    """Base class for search engines"""
    
    async def search(self, query: str, page=None) -> List[Dict[str, Any]]:
        """Perform search and return results"""
        raise NotImplementedError


class GoogleSearch(SearchEngine):
    """Google search without API key"""
    
    async def search(self, query: str, page=None) -> List[Dict[str, Any]]:
        """Search Google and extract results"""
        from playwright.async_api import async_playwright
        
        results = []
        browser = None
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--disable-blink-features=AutomationControlled']
                )
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                page = await context.new_page()
                
                search_url = f"https://www.google.com/search?q={quote_plus(query)}"
                logger.debug(f"Google search: {search_url}")
                
                await page.goto(search_url, wait_until='networkidle', timeout=15000)
                await page.wait_for_selector('div#search', timeout=5000)
                
                # Extract search results
                search_divs = await page.query_selector_all('div.g')
                
                for div in search_divs[:5]:
                    try:
                        title_elem = await div.query_selector('h3')
                        title = await title_elem.inner_text() if title_elem else ''
                        
                        link_elem = await div.query_selector('a')
                        url = await link_elem.get_attribute('href') if link_elem else ''
                        
                        snippet_elem = await div.query_selector('span.aCOpRe, div.VwiC3b')
                        snippet = await snippet_elem.inner_text() if snippet_elem else ''
                        
                        if url and title:
                            results.append({
                                'title': title,
                                'url': url,
                                'snippet': snippet,
                                'source': 'google'
                            })
                    except Exception as e:
                        logger.debug(f"Error extracting result: {e}")
                        continue
                
                await browser.close()
                
        except Exception as e:
            logger.error(f"Google search failed: {str(e)}")
            if browser:
                await browser.close()
            raise
        
        return results


class DuckDuckGoSearch(SearchEngine):
    """DuckDuckGo search without API key"""
    
    async def search(self, query: str, page=None) -> List[Dict[str, Any]]:
        """Search DuckDuckGo and extract results"""
        from playwright.async_api import async_playwright
        
        results = []
        browser = None
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--disable-blink-features=AutomationControlled']
                )
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                page = await context.new_page()
                
                search_url = f"https://duckduckgo.com/?q={quote_plus(query)}"
                logger.debug(f"DuckDuckGo search: {search_url}")
                
                await page.goto(search_url, wait_until='networkidle', timeout=15000)
                
                # Wait for results to load
                await page.wait_for_selector('article[data-testid="result"]', timeout=5000)
                
                # Extract search results
                result_articles = await page.query_selector_all('article[data-testid="result"]')
                
                for article in result_articles[:5]:
                    try:
                        # Get title and URL
                        link_elem = await article.query_selector('h2 a')
                        if link_elem:
                            title = await link_elem.inner_text()
                            url = await link_elem.get_attribute('href')
                        else:
                            continue
                        
                        # Get snippet
                        snippet_elem = await article.query_selector('div[data-result="snippet"]')
                        snippet = await snippet_elem.inner_text() if snippet_elem else ''
                        
                        if url and title:
                            results.append({
                                'title': title,
                                'url': url,
                                'snippet': snippet,
                                'source': 'duckduckgo'
                            })
                    except Exception as e:
                        logger.debug(f"Error extracting DDG result: {e}")
                        continue
                
                await browser.close()
                
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {str(e)}")
            if browser:
                await browser.close()
            raise
        
        return results


class BingSearch(SearchEngine):
    """Bing search without API key (additional fallback)"""
    
    async def search(self, query: str, page=None) -> List[Dict[str, Any]]:
        """Search Bing and extract results"""
        from playwright.async_api import async_playwright
        
        results = []
        browser = None
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--disable-blink-features=AutomationControlled']
                )
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                page = await context.new_page()
                
                search_url = f"https://www.bing.com/search?q={quote_plus(query)}"
                logger.debug(f"Bing search: {search_url}")
                
                await page.goto(search_url, wait_until='networkidle', timeout=15000)
                await page.wait_for_selector('#b_results', timeout=5000)
                
                # Extract search results
                result_items = await page.query_selector_all('li.b_algo')
                
                for item in result_items[:5]:
                    try:
                        # Get title and URL
                        link_elem = await item.query_selector('h2 a')
                        if link_elem:
                            title = await link_elem.inner_text()
                            url = await link_elem.get_attribute('href')
                        else:
                            continue
                        
                        # Get snippet
                        snippet_elem = await item.query_selector('.b_caption p')
                        snippet = await snippet_elem.inner_text() if snippet_elem else ''
                        
                        if url and title:
                            results.append({
                                'title': title,
                                'url': url,
                                'snippet': snippet,
                                'source': 'bing'
                            })
                    except Exception as e:
                        logger.debug(f"Error extracting Bing result: {e}")
                        continue
                
                await browser.close()
                
        except Exception as e:
            logger.error(f"Bing search failed: {str(e)}")
            if browser:
                await browser.close()
            raise
        
        return results


class MultiEngineSearch:
    """Search with multiple engines and fallback support"""
    
    def __init__(self):
        self.engines = [
            ('Google', GoogleSearch()),
            ('DuckDuckGo', DuckDuckGoSearch()),
            ('Bing', BingSearch())
        ]
    
    async def search(self, query: str, max_retries: int = 3) -> Dict[str, Any]:
        """
        Search with fallback to multiple engines.
        
        Returns:
            Dict with results and metadata about which engine succeeded
        """
        results = {
            'query': query,
            'results': [],
            'engine_used': None,
            'engines_tried': [],
            'success': False,
            'error': None
        }
        
        for engine_name, engine in self.engines:
            results['engines_tried'].append(engine_name)
            
            try:
                logger.info(f"Searching with {engine_name}: {query}")
                search_results = await engine.search(query)
                
                if search_results:
                    results['results'] = search_results
                    results['engine_used'] = engine_name
                    results['success'] = True
                    logger.info(f"Successfully found {len(search_results)} results with {engine_name}")
                    break
                else:
                    logger.warning(f"No results from {engine_name}")
                    
            except Exception as e:
                logger.error(f"{engine_name} search failed: {str(e)}")
                results['error'] = str(e)
                
                # Try next engine
                if engine_name != self.engines[-1][0]:
                    logger.info(f"Falling back to next search engine...")
                    await asyncio.sleep(1)  # Brief pause before retry
                continue
        
        if not results['success']:
            logger.error(f"All search engines failed for query: {query}")
        
        return results


# Convenience function
async def search_web(query: str) -> Dict[str, Any]:
    """
    Search the web using multiple engines with fallback.
    
    Args:
        query: Search query string
        
    Returns:
        Dict with search results and metadata
    """
    searcher = MultiEngineSearch()
    return await searcher.search(query)