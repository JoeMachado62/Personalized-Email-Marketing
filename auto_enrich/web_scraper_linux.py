"""
Simplified web scraper for Linux environment.
No Windows-specific workarounds needed.
"""

import logging
import os
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Check for Serper API first (most reliable)
USE_SERPER = os.environ.get('SERPER_API_KEY') is not None

if USE_SERPER:
    logger.info("Using Serper API for search (fast, reliable, no browser windows!)")
    from .web_scraper_serper import SerperWebGatherer as WebDataGatherer, search_web
else:
    # On Linux, Playwright works without issues
    try:
        from .web_scraper_playwright import PlaywrightWebGatherer as WebDataGatherer, search_web
        logger.info("Using Playwright implementation")
    except ImportError:
        # Fallback to Selenium if needed
        from .web_scraper_selenium import SeleniumWebGatherer as WebDataGatherer, search_web
        logger.info("Using Selenium implementation")

# Backward compatibility wrapper function
async def gather_web_data(
    company_name: str,
    location: str = "",
    additional_data: Optional[Dict] = None,
    phone: str = "",
    campaign_context: Optional[Dict] = None,
    search_provider: str = "auto",
    use_mcp_fetch: bool = True
) -> Dict[str, Any]:
    """
    Backward compatibility wrapper for web data gathering.
    """
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