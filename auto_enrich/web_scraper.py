"""
Enhanced web scraper that automatically uses Playwright if available, falls back to Selenium.
This follows the architectural design: Search -> Scrape -> AI Interpret -> Store
Uses migration adapter to seamlessly switch between implementations.
"""

import asyncio
import logging
import os
import sys
from typing import Dict, Any, Optional

# Import config to load environment variables from .env file
from . import config

logger = logging.getLogger(__name__)

# Check for Serper API first (most reliable)
USE_SERPER = os.environ.get('SERPER_API_KEY') is not None
USE_PLAYWRIGHT = os.environ.get('USE_PLAYWRIGHT', 'true').lower() == 'true' if not USE_SERPER else False

# Use Serper API if available (fastest and most reliable)
if USE_SERPER:
    logger.info("Using FOCUSED Serper Maps + Sunbiz approach for high-quality data!")
    from .focused_web_scraper import FocusedWebGatherer as WebDataGatherer
    from .serper_client import search_with_serper as search_web
    
# Windows-specific handling for Playwright
elif USE_PLAYWRIGHT and sys.platform == 'win32':
    try:
        # Check if we're in a running event loop (FastAPI/uvicorn)
        asyncio.get_running_loop()
        # We're in an existing loop - use enhanced subprocess wrapper for Windows
        logger.info("Windows detected with existing event loop - using enhanced Playwright subprocess wrapper")
        from .playwright_subprocess_wrapper_v2 import WindowsPlaywrightGatherer as WebDataGatherer
        from .playwright_subprocess_wrapper_v2 import PlaywrightSubprocessWrapperV2
        
        async def search_web(query, **kwargs):
            wrapper = PlaywrightSubprocessWrapperV2()
            return await wrapper.search_web(query, kwargs.get('max_results', 10))
            
    except RuntimeError:
        # No event loop - safe to use Playwright directly
        try:
            from .web_scraper_playwright import PlaywrightWebGatherer as WebDataGatherer, search_web
            logger.info("Using Playwright implementation (direct mode)")
        except (ImportError, Exception) as e:
            logger.warning(f"Playwright error ({e}), falling back to Selenium")
            from .web_scraper_selenium import SeleniumWebGatherer as WebDataGatherer, search_web
            
elif USE_PLAYWRIGHT:
    # Non-Windows systems can use Playwright directly
    try:
        from .web_scraper_playwright import PlaywrightWebGatherer as WebDataGatherer, search_web
        logger.info("Using Playwright implementation (anti-detection enabled)")
    except (ImportError, Exception) as e:
        logger.warning(f"Playwright error ({e}), falling back to Selenium (browser windows will open!)")
        from .web_scraper_selenium import SeleniumWebGatherer as WebDataGatherer, search_web
else:
    # Explicitly use Selenium if requested
    from .web_scraper_selenium import SeleniumWebGatherer as WebDataGatherer, search_web
    logger.info("Using Selenium implementation (USE_PLAYWRIGHT=false)")

# Don't log at import time - can cause issues
# logger.info("Using Selenium + Markdownify implementation")

# Backward compatibility wrapper function
async def gather_web_data(
    company_name: str,
    location: str = "",
    additional_data: Optional[Dict] = None,
    phone: str = "",
    campaign_context: Optional[Dict] = None,
    search_provider: str = "selenium"
) -> Dict[str, Any]:
    """
    Backward compatibility wrapper for web data gathering.
    
    Args:
        company_name: Company name to search
        location: Location/address information
        additional_data: Additional data dictionary (phone, email, etc.)
        phone: Phone number (optional, legacy parameter)
        campaign_context: Campaign context for targeted searches
        search_provider: Search provider (uses configured implementation)
        
    Returns:
        Dictionary with gathered web data
    """
    # Use the configured WebDataGatherer (Playwright or Selenium)
    async with WebDataGatherer() as gatherer:
        # Handle both new additional_data dict and legacy phone parameter
        if not additional_data:
            additional_data = {}
        if phone and 'phone' not in additional_data:
            additional_data['phone'] = phone
        
        # Pass to the search_and_gather method
        return await gatherer.search_and_gather(
            company_name=company_name,
            location=location,
            additional_data=additional_data if additional_data else None,
            campaign_context=campaign_context
        )