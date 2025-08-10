"""
Enhanced web scraper using Selenium and MCP Fetch.
This follows the architectural design: Search -> Scrape -> AI Interpret -> Store
NO PLAYWRIGHT - uses Selenium for search and MCP Fetch for content extraction.
"""

import asyncio
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Import the Selenium-only implementation
from .web_scraper_selenium import SeleniumWebGatherer, search_web

# Use the Selenium implementation
WebDataGatherer = SeleniumWebGatherer

# Don't log at import time - can cause issues
# logger.info("Using Selenium + MCP Fetch implementation")

# Backward compatibility wrapper function
async def gather_web_data(
    company_name: str,
    location: str = "",
    additional_data: Optional[Dict] = None,
    phone: str = "",
    campaign_context: Optional[Dict] = None,
    search_provider: str = "selenium",
    use_mcp_fetch: bool = True
) -> Dict[str, Any]:
    """
    Backward compatibility wrapper for the new SeleniumWebGatherer.
    
    Args:
        company_name: Company name to search
        location: Location/address information
        additional_data: Additional data dictionary (phone, email, etc.)
        phone: Phone number (optional, legacy parameter)
        campaign_context: Campaign context for targeted searches
        search_provider: Search provider (always selenium now)
        use_mcp_fetch: Whether to use MCP Fetch for content extraction
        
    Returns:
        Dictionary with gathered web data
    """
    # SeleniumWebGatherer doesn't take init parameters
    async with SeleniumWebGatherer() as gatherer:
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