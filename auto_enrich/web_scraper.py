"""
Enhanced web scraper using Selenium and MCP Fetch.
This follows the architectural design: Search -> Scrape -> AI Interpret -> Store
NO PLAYWRIGHT - uses Selenium for search and MCP Fetch for content extraction.
"""

import asyncio
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Import the Selenium-only implementation
from .web_scraper_selenium import SeleniumWebGatherer, search_web

# Use the Selenium implementation
WebDataGatherer = SeleniumWebGatherer

logger.info("Using Selenium + MCP Fetch implementation")