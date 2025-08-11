"""
Windows-compatible Playwright wrapper that runs in a subprocess.
This solves the asyncio ProactorEventLoop issue by isolating Playwright.
"""

import asyncio
import sys
import json
import subprocess
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class PlaywrightSubprocessWrapper:
    """
    Runs Playwright operations in a subprocess to avoid Windows event loop conflicts.
    This ensures Playwright gets the ProactorEventLoop it needs without affecting FastAPI.
    """
    
    @staticmethod
    async def search_web(query: str, max_results: int = 10) -> list:
        """
        Run web search in subprocess.
        
        Args:
            query: Search query
            max_results: Maximum results to return
            
        Returns:
            List of search results
        """
        script = f"""
import asyncio
import sys
import json

# Set Windows event loop
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

async def run_search():
    from auto_enrich.search_with_playwright import search_with_playwright
    results = await search_with_playwright("{query}", headless=True, max_results={max_results})
    return results

results = asyncio.run(run_search())
print(json.dumps(results))
"""
        
        try:
            result = subprocess.run(
                [sys.executable, "-c", script],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"Search subprocess failed: {result.stderr}")
                return []
            
            return json.loads(result.stdout)
            
        except subprocess.TimeoutExpired:
            logger.error("Search subprocess timed out")
            return []
        except Exception as e:
            logger.error(f"Search subprocess error: {e}")
            return []
    
    @staticmethod
    async def scrape_url(url: str) -> Dict[str, Any]:
        """
        Scrape a URL in subprocess.
        
        Args:
            url: URL to scrape
            
        Returns:
            Scraped data dictionary
        """
        script = f"""
import asyncio
import sys
import json

# Set Windows event loop
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

async def run_scrape():
    from auto_enrich.web_scraper_playwright import PlaywrightWebGatherer
    
    async with PlaywrightWebGatherer() as gatherer:
        data = await gatherer.scrape_website("{url}")
        return data

data = asyncio.run(run_scrape())
print(json.dumps(data))
"""
        
        try:
            result = subprocess.run(
                [sys.executable, "-c", script],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"Scrape subprocess failed: {result.stderr}")
                return {}
            
            return json.loads(result.stdout)
            
        except subprocess.TimeoutExpired:
            logger.error("Scrape subprocess timed out")
            return {}
        except Exception as e:
            logger.error(f"Scrape subprocess error: {e}")
            return {}
    
    @staticmethod
    async def gather_web_data(company_name: str, location: str = "", 
                            additional_data: Optional[Dict] = None,
                            campaign_context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Full web data gathering in subprocess.
        
        Args:
            company_name: Company name to search
            location: Location information
            additional_data: Additional context data
            
        Returns:
            Complete gathered data
        """
        # Escape quotes in inputs
        company_name = company_name.replace('"', '\\"')
        location = location.replace('"', '\\"')
        additional_json = json.dumps(additional_data or {})
        campaign_json = json.dumps(campaign_context or {})
        
        script = f"""
import asyncio
import sys
import json

# Set Windows event loop
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

async def run_gather():
    from auto_enrich.web_scraper_playwright import PlaywrightWebGatherer
    
    async with PlaywrightWebGatherer() as gatherer:
        data = await gatherer.search_and_gather(
            company_name="{company_name}",
            location="{location}",
            additional_data={additional_json},
            campaign_context={campaign_json}
        )
        return data

data = asyncio.run(run_gather())
print(json.dumps(data))
"""
        
        try:
            result = subprocess.run(
                [sys.executable, "-c", script],
                capture_output=True,
                text=True,
                timeout=90
            )
            
            if result.returncode != 0:
                logger.error(f"Gather subprocess failed: {result.stderr}")
                # Fallback to empty results
                return {
                    'search_results': [],
                    'website_found': False,
                    'website_url': None,
                    'website_data': {},
                    'confidence_score': 0.0
                }
            
            return json.loads(result.stdout)
            
        except subprocess.TimeoutExpired:
            logger.error("Gather subprocess timed out")
            return {
                'search_results': [],
                'website_found': False,
                'website_url': None,
                'website_data': {},
                'confidence_score': 0.0
            }
        except Exception as e:
            logger.error(f"Gather subprocess error: {e}")
            return {
                'search_results': [],
                'website_found': False,
                'website_url': None,
                'website_data': {},
                'confidence_score': 0.0
            }


# Compatibility function for existing code
async def gather_web_data_subprocess(company_name: str, location: str = "",
                                    additional_data: Optional[Dict] = None,
                                    **kwargs) -> Dict[str, Any]:
    """
    Wrapper function that uses subprocess for Windows compatibility.
    """
    wrapper = PlaywrightSubprocessWrapper()
    return await wrapper.gather_web_data(company_name, location, additional_data)