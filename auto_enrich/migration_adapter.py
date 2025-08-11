"""
Migration adapter to seamlessly switch between Selenium and Playwright implementations.
This module provides a unified interface that automatically uses Playwright if available,
or falls back to Selenium if needed.
"""

import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Environment variable to control which implementation to use
USE_PLAYWRIGHT = os.environ.get('USE_PLAYWRIGHT', 'true').lower() == 'true'


def get_search_implementation():
    """
    Get the appropriate search implementation based on configuration.
    
    Returns:
        Search class or function
    """
    if USE_PLAYWRIGHT:
        try:
            from .search_with_playwright import PlaywrightSearch, search_with_real_chrome
            logger.info("Using Playwright for search (anti-detection enabled)")
            return search_with_real_chrome
        except ImportError as e:
            logger.warning(f"Playwright search not available: {e}, falling back to Selenium")
    
    # Fallback to Selenium
    try:
        from .search_with_selenium import search_with_real_chrome
        logger.info("Using Selenium for search (legacy mode)")
        return search_with_real_chrome
    except ImportError as e:
        logger.error(f"Neither Playwright nor Selenium search available: {e}")
        raise


def get_scraper_implementation():
    """
    Get the appropriate web scraper implementation.
    
    Returns:
        Web scraper class
    """
    if USE_PLAYWRIGHT:
        try:
            from .web_scraper_playwright import PlaywrightWebGatherer
            logger.info("Using Playwright for web scraping (stealth mode)")
            return PlaywrightWebGatherer
        except ImportError as e:
            logger.warning(f"Playwright scraper not available: {e}, falling back to Selenium")
    
    # Fallback to Selenium
    try:
        from .web_scraper_selenium import SeleniumWebGatherer
        logger.info("Using Selenium for web scraping (legacy mode)")
        return SeleniumWebGatherer
    except ImportError as e:
        logger.error(f"Neither Playwright nor Selenium scraper available: {e}")
        raise


class UniversalSearch:
    """
    Universal search interface that works with both Playwright and Selenium.
    """
    
    def __init__(self, headless: bool = True):
        """
        Initialize universal search.
        
        Args:
            headless: Run browser in headless mode
        """
        self.headless = headless
        self.implementation = None
        self._setup_implementation()
    
    def _setup_implementation(self):
        """Setup the appropriate implementation."""
        if USE_PLAYWRIGHT:
            try:
                from .search_with_playwright import PlaywrightSearch
                self.implementation = PlaywrightSearch(headless=self.headless)
                self.backend = 'playwright'
                logger.debug("UniversalSearch using Playwright backend")
            except ImportError:
                self._setup_selenium()
        else:
            self._setup_selenium()
    
    def _setup_selenium(self):
        """Setup Selenium implementation."""
        try:
            from .search_with_selenium import RealChromeSearch
            self.implementation = RealChromeSearch(headless=self.headless)
            self.backend = 'selenium'
            logger.debug("UniversalSearch using Selenium backend")
        except ImportError as e:
            raise ImportError(f"No search implementation available: {e}")
    
    async def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search using the available implementation.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of search results
        """
        if self.backend == 'playwright':
            # Playwright is async
            return await self.implementation.search_google(query, max_results)
        else:
            # Selenium is sync, wrap in async
            import asyncio
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                self.implementation.search_google,
                query
            )
    
    def search_sync(self, query: str) -> List[Dict[str, Any]]:
        """
        Synchronous search for backward compatibility.
        
        Args:
            query: Search query
            
        Returns:
            List of search results
        """
        if self.backend == 'playwright':
            # Run async in sync context
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    raise RuntimeError
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            return loop.run_until_complete(
                self.implementation.search_google(query, 10)
            )
        else:
            # Selenium is already sync
            return self.implementation.search_google(query)
    
    def cleanup(self):
        """Cleanup resources."""
        if self.backend == 'selenium' and hasattr(self.implementation, 'close'):
            self.implementation.close()
        elif self.backend == 'playwright':
            # Playwright cleanup handled by browser manager
            pass


class UniversalWebGatherer:
    """
    Universal web gatherer that works with both implementations.
    """
    
    def __init__(self, headless: bool = True):
        """
        Initialize universal web gatherer.
        
        Args:
            headless: Run browser in headless mode
        """
        self.headless = headless
        self.implementation_class = get_scraper_implementation()
        self.implementation = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.implementation = self.implementation_class()
        if hasattr(self.implementation, '__aenter__'):
            await self.implementation.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if hasattr(self.implementation, '__aexit__'):
            await self.implementation.__aexit__(exc_type, exc_val, exc_tb)
    
    async def search_and_gather(self, company_name: str, location: str,
                               additional_data: Dict[str, str] = None,
                               campaign_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Search and gather data using available implementation.
        
        Args:
            company_name: Company name
            location: Location
            additional_data: Additional data
            campaign_context: Campaign context
            
        Returns:
            Gathered data dictionary
        """
        return await self.implementation.search_and_gather(
            company_name=company_name,
            location=location,
            additional_data=additional_data,
            campaign_context=campaign_context
        )


# Convenience functions for easy migration
def search_web_universal(query: str, headless: bool = True) -> List[Dict[str, Any]]:
    """
    Universal search function that works with any backend.
    
    Args:
        query: Search query
        headless: Run in headless mode
        
    Returns:
        Search results
    """
    search_func = get_search_implementation()
    return search_func(query, headless)


async def search_web_universal_async(query: str, headless: bool = True) -> List[Dict[str, Any]]:
    """
    Async universal search function.
    
    Args:
        query: Search query
        headless: Run in headless mode
        
    Returns:
        Search results
    """
    searcher = UniversalSearch(headless=headless)
    return await searcher.search(query)


# Migration status checker
def check_migration_status() -> Dict[str, Any]:
    """
    Check the status of the Playwright migration.
    
    Returns:
        Dictionary with migration status information
    """
    status = {
        'playwright_available': False,
        'selenium_available': False,
        'current_backend': None,
        'migration_complete': False,
        'recommendations': []
    }
    
    # Check Playwright
    try:
        import playwright
        from .search_with_playwright import PlaywrightSearch
        from .web_scraper_playwright import PlaywrightWebGatherer
        status['playwright_available'] = True
    except ImportError:
        status['recommendations'].append("Install Playwright: pip install playwright>=1.40")
        status['recommendations'].append("Install browsers: playwright install")
    
    # Check Selenium
    try:
        import selenium
        from .search_with_selenium import RealChromeSearch
        from .web_scraper_selenium import SeleniumWebGatherer
        status['selenium_available'] = True
    except ImportError:
        pass
    
    # Determine current backend
    if USE_PLAYWRIGHT and status['playwright_available']:
        status['current_backend'] = 'playwright'
        status['migration_complete'] = True
    elif status['selenium_available']:
        status['current_backend'] = 'selenium'
        if status['playwright_available']:
            status['recommendations'].append("Set USE_PLAYWRIGHT=true to use Playwright")
    else:
        status['current_backend'] = None
        status['recommendations'].append("No backend available! Install Playwright or Selenium")
    
    # Additional recommendations
    if status['current_backend'] == 'selenium':
        status['recommendations'].append("Selenium is deprecated, migrate to Playwright for better performance")
        status['recommendations'].append("Selenium opens visible browser windows - use Playwright for headless operation")
    
    if status['migration_complete']:
        status['recommendations'].append("Migration complete! Consider removing Selenium dependencies")
    
    return status


if __name__ == "__main__":
    # Check migration status
    import json
    
    print("="*60)
    print("MIGRATION STATUS CHECK")
    print("="*60)
    
    status = check_migration_status()
    
    print(f"\nPlaywright Available: {status['playwright_available']}")
    print(f"Selenium Available: {status['selenium_available']}")
    print(f"Current Backend: {status['current_backend'] or 'NONE'}")
    print(f"Migration Complete: {status['migration_complete']}")
    
    if status['recommendations']:
        print("\nRecommendations:")
        for i, rec in enumerate(status['recommendations'], 1):
            print(f"{i}. {rec}")
    
    print("\n" + "="*60)