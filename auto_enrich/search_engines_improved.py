"""
Improved search engines with better reliability and bot evasion.
Uses direct HTTP requests as primary method, Playwright as fallback.
"""

import asyncio
import logging
import re
import random
import json
from typing import Dict, List, Optional, Any
from urllib.parse import quote_plus, unquote
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class GoogleSearchImproved:
    """Google search using multiple methods for better reliability"""
    
    async def search(self, query: str) -> List[Dict[str, Any]]:
        """Try multiple methods to search Google"""
        
        # Method 1: Try direct HTTP request first (faster, more reliable)
        try:
            results = await self._search_via_http(query)
            if results:
                logger.info(f"Google HTTP search successful: {len(results)} results")
                return results
        except Exception as e:
            logger.debug(f"Google HTTP search failed: {e}")
        
        # Method 2: Use Google Custom Search JSON API (no key needed for basic search)
        try:
            results = await self._search_via_json_api(query)
            if results:
                logger.info(f"Google JSON API search successful: {len(results)} results")
                return results
        except Exception as e:
            logger.debug(f"Google JSON API search failed: {e}")
        
        # Method 3: Fall back to Playwright if HTTP methods fail
        try:
            results = await self._search_via_playwright(query)
            if results:
                logger.info(f"Google Playwright search successful: {len(results)} results")
                return results
        except Exception as e:
            logger.debug(f"Google Playwright search failed: {e}")
        
        logger.error(f"All Google search methods failed for query: {query}")
        return []
    
    async def _search_via_http(self, query: str) -> List[Dict[str, Any]]:
        """Direct HTTP request to Google search"""
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        params = {
            'q': query,
            'hl': 'en',
            'gl': 'us',
            'num': 10
        }
        
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            # Add random delay to avoid rate limiting
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            response = await client.get(
                'https://www.google.com/search',
                params=params,
                headers=headers
            )
            
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}")
            
            return self._parse_html_results(response.text)
    
    def _parse_html_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse Google search results from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # Find all result divs - Google uses various classes
        result_divs = soup.find_all('div', class_='g')
        if not result_divs:
            result_divs = soup.find_all('div', class_='hlcw0c')
        
        for div in result_divs[:5]:
            try:
                # Extract title
                title_elem = div.find('h3')
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)
                
                # Extract URL
                link_elem = div.find('a', href=True)
                if not link_elem:
                    continue
                url = link_elem['href']
                
                # Clean Google redirect URLs
                if url.startswith('/url?'):
                    url = unquote(url.split('q=')[1].split('&')[0])
                
                # Extract snippet
                snippet = ''
                snippet_elem = div.find('span', class_='aCOpRe') or div.find('div', class_='VwiC3b')
                if snippet_elem:
                    snippet = snippet_elem.get_text(strip=True)
                
                if url and title and 'google.com' not in url:
                    results.append({
                        'title': title,
                        'url': url,
                        'snippet': snippet,
                        'source': 'google_http'
                    })
            except Exception as e:
                logger.debug(f"Error parsing result: {e}")
                continue
        
        return results
    
    async def _search_via_json_api(self, query: str) -> List[Dict[str, Any]]:
        """Try using Google's JSON API endpoint (undocumented but sometimes works)"""
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'
        }
        
        params = {
            'q': query,
            'num': 5
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try Google's AJAX endpoint
            response = await client.get(
                'https://www.google.com/complete/search',
                params={
                    'q': query,
                    'cp': '1',
                    'client': 'psy-ab',
                    'xssi': 't',
                    'gs_ri': 'gws-wiz',
                    'hl': 'en-US'
                },
                headers=headers
            )
            
            if response.status_code == 200:
                # Parse the JSONP response
                text = response.text
                if text.startswith(")]}\'"):
                    text = text[5:]
                
                try:
                    data = json.loads(text)
                    # Extract suggestions as fallback results
                    suggestions = data[1] if len(data) > 1 else []
                    results = []
                    for i, suggestion in enumerate(suggestions[:5]):
                        results.append({
                            'title': suggestion[0] if isinstance(suggestion, list) else str(suggestion),
                            'url': f"https://www.google.com/search?q={quote_plus(str(suggestion[0] if isinstance(suggestion, list) else suggestion))}",
                            'snippet': 'Search suggestion',
                            'source': 'google_suggestions'
                        })
                    return results
                except:
                    pass
        
        return []
    
    async def _search_via_playwright(self, query: str) -> List[Dict[str, Any]]:
        """Fallback to Playwright with improved bot evasion"""
        from playwright.async_api import async_playwright
        
        results = []
        browser = None
        
        try:
            async with async_playwright() as p:
                # Use more realistic browser settings
                browser = await p.chromium.launch(
                    headless=True,  # Keep headless for server environments
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-accelerated-2d-canvas',
                        '--no-gpu',
                        '--window-size=1920,1080'
                    ]
                )
                
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    locale='en-US'
                )
                
                page = await context.new_page()
                
                # Add anti-detection scripts
                await page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """)
                
                # Direct navigation with query in URL (faster, more reliable)
                search_url = f"https://www.google.com/search?q={quote_plus(query)}&hl=en"
                await page.goto(search_url, wait_until='domcontentloaded', timeout=10000)
                
                # Wait a bit for results to load
                await asyncio.sleep(1)
                
                # Extract results using JavaScript (more reliable than selectors)
                results = await page.evaluate("""
                    () => {
                        const results = [];
                        const resultDivs = document.querySelectorAll('div.g, div[data-sokoban-container]');
                        
                        for (let div of resultDivs) {
                            const titleElem = div.querySelector('h3');
                            const linkElem = div.querySelector('a[href]');
                            const snippetElem = div.querySelector('span.aCOpRe, div.VwiC3b, div.IsZvec');
                            
                            if (titleElem && linkElem) {
                                const url = linkElem.href;
                                if (!url.includes('google.com')) {
                                    results.push({
                                        title: titleElem.innerText,
                                        url: url,
                                        snippet: snippetElem ? snippetElem.innerText : '',
                                        source: 'google_playwright'
                                    });
                                }
                            }
                            
                            if (results.length >= 5) break;
                        }
                        
                        return results;
                    }
                """)
                
                await browser.close()
                return results
                
        except Exception as e:
            logger.error(f"Playwright search error: {str(e)}")
            if browser:
                await browser.close()
            raise


class DuckDuckGoSearchImproved:
    """Improved DuckDuckGo search"""
    
    async def search(self, query: str) -> List[Dict[str, Any]]:
        """Search DuckDuckGo using HTTP requests"""
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1'
        }
        
        params = {
            'q': query,
            't': 'h_',
            'ia': 'web'
        }
        
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
                response = await client.get(
                    'https://html.duckduckgo.com/html/',
                    params=params,
                    headers=headers
                )
                
                if response.status_code == 200:
                    return self._parse_ddg_results(response.text)
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
        
        return []
    
    def _parse_ddg_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse DuckDuckGo results from HTML"""
        from urllib.parse import unquote, parse_qs, urlparse
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # Find result links
        result_links = soup.find_all('a', class_='result__a')
        
        for link in result_links[:5]:
            try:
                title = link.get_text(strip=True)
                raw_url = link.get('href', '')
                
                # Extract actual URL from DuckDuckGo redirect
                actual_url = ''
                if raw_url.startswith('//duckduckgo.com/l/'):
                    # Parse the redirect URL
                    if '?uddg=' in raw_url:
                        params = raw_url.split('?uddg=')[1]
                        if '&' in params:
                            params = params.split('&')[0]
                        actual_url = unquote(params)
                elif raw_url.startswith('http'):
                    actual_url = raw_url
                else:
                    # Handle relative URLs
                    if '?uddg=' in raw_url:
                        params = raw_url.split('?uddg=')[1]
                        if '&' in params:
                            params = params.split('&')[0]
                        actual_url = unquote(params)
                
                # Get snippet from parent result div
                parent = link.find_parent('div', class_='result')
                snippet = ''
                if parent:
                    snippet_elem = parent.find('a', class_='result__snippet')
                    if snippet_elem:
                        snippet = snippet_elem.get_text(strip=True)
                
                if actual_url and title:
                    results.append({
                        'title': title,
                        'url': actual_url,
                        'snippet': snippet,
                        'source': 'duckduckgo_http'
                    })
                    logger.debug(f"Found DDG result: {title} - {actual_url}")
            except Exception as e:
                logger.debug(f"Error parsing DDG result: {e}")
                continue
        
        logger.info(f"DuckDuckGo found {len(results)} results")
        return results


class MultiEngineSearchImproved:
    """Improved multi-engine search with better reliability"""
    
    def __init__(self):
        self.engines = [
            ('Google', GoogleSearchImproved()),
            ('DuckDuckGo', DuckDuckGoSearchImproved())
        ]
    
    async def search(self, query: str) -> Dict[str, Any]:
        """Search with multiple engines and methods"""
        
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
                logger.info(f"Trying {engine_name} for: {query}")
                search_results = await engine.search(query)
                
                if search_results:
                    results['results'] = search_results
                    results['engine_used'] = engine_name
                    results['success'] = True
                    logger.info(f"Success with {engine_name}: {len(search_results)} results")
                    return results
                    
            except Exception as e:
                logger.error(f"{engine_name} failed: {str(e)}")
                results['error'] = str(e)
                continue
        
        logger.error(f"All search engines failed for: {query}")
        return results


# Convenience function
async def search_web_improved(query: str) -> Dict[str, Any]:
    """Use improved search engines"""
    searcher = MultiEngineSearchImproved()
    return await searcher.search(query)