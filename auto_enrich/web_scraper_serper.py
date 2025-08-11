"""
Web scraper using Serper API for search and MCP for content extraction.
Fast, reliable, no browser windows, no detection issues.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

from .serper_client import SerperClient, search_with_serper
try:
    from .enhanced_content_extractor import EnhancedContentExtractor as MCPContentExtractor
except ImportError:
    try:
        from .mcp_fetch_client import SimpleMCPExtractor as MCPContentExtractor
    except ImportError:
        from .mcp_client import MCPContentExtractor

logger = logging.getLogger(__name__)


class SerperWebGatherer:
    """
    Web data gatherer using Serper API for search and MCP for content.
    The most reliable and scalable solution.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Serper web gatherer.
        
        Args:
            api_key: Serper API key (or uses environment variable)
        """
        self.serper = SerperClient(api_key)
        self.mcp_extractor = MCPContentExtractor()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, *args):
        """Async context manager exit."""
        pass
    
    async def search_and_gather(self, company_name: str, location: str = "",
                               additional_data: Optional[Dict] = None,
                               campaign_context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Main method: Search for company using Serper, scrape using MCP.
        
        Args:
            company_name: Name of the business
            location: Location/address information
            additional_data: Additional context (phone, email, etc.)
            campaign_context: Campaign configuration for targeted search
            
        Returns:
            Dictionary with all gathered web data
        """
        gathered_data = {
            'search_results': [],
            'website_found': False,
            'website_url': None,
            'website_data': {},
            'confidence_score': 0.0
        }
        
        try:
            # Step 1: Search using Serper API (fast and reliable)
            logger.info(f"Searching with Serper API for: {company_name} {location}")
            search_results = await self.serper.search_business(company_name, location)
            
            if search_results:
                gathered_data['search_results'] = search_results
                gathered_data['search_engine'] = 'serper'
                logger.info(f"Serper found {len(search_results)} results")
                
                # Step 2: Identify official website
                website_url = self._identify_official_website(search_results, company_name)
                if website_url:
                    gathered_data['website_found'] = True
                    gathered_data['website_url'] = website_url
                    gathered_data['confidence_score'] = 0.8
                    logger.info(f"Identified website: {website_url}")
                    
                    # Step 3: Extract website content using MCP
                    try:
                        website_content = await self.mcp_extractor.extract(website_url)
                        if website_content:
                            gathered_data['website_data'] = website_content
                            gathered_data['confidence_score'] = 0.9
                            logger.info("Successfully extracted website content with MCP")
                    except Exception as e:
                        logger.warning(f"MCP extraction failed, using basic extraction: {e}")
                        # Fallback to basic extraction from search results
                        gathered_data['website_data'] = self._extract_from_search_results(search_results)
                
                # Step 4: Extract additional data from search results
                gathered_data['extracted_contacts'] = self._extract_contact_info(search_results)
                
                # Step 5: Process Google My Business data if available
                gmb_data = self._extract_gmb_data(search_results)
                if gmb_data:
                    gathered_data['gmb_data'] = gmb_data
                    gathered_data['confidence_score'] = min(1.0, gathered_data['confidence_score'] + 0.1)
                
            else:
                logger.warning(f"No search results found for {company_name}")
                gathered_data['error'] = "No search results found"
                
        except Exception as e:
            logger.error(f"Error in search_and_gather: {str(e)}")
            gathered_data['error'] = str(e)
        
        return gathered_data
    
    def _identify_official_website(self, search_results: List[Dict], 
                                  company_name: str) -> Optional[str]:
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
        
        # Priority 1: GMB website or knowledge graph website
        for result in search_results:
            if result.get('is_gmb') or result.get('source') == 'serper_knowledge':
                website = result.get('website') or result.get('url')
                if website and not website.startswith('https://www.google.com'):
                    return website
        
        # Priority 2: First result with company name in domain
        company_words = [w.lower() for w in company_name.split() if len(w) > 3]
        for result in search_results:
            url = result.get('url', '')
            if url:
                domain = urlparse(url).netloc.lower()
                if any(word in domain for word in company_words):
                    return url
        
        # Priority 3: First non-directory result
        directories = [
            'yelp.', 'yellowpages.', 'facebook.', 'linkedin.',
            'twitter.', 'instagram.', 'bbb.org', 'manta.com'
        ]
        
        for result in search_results:
            url = result.get('url', '')
            if url:
                domain = urlparse(url).netloc.lower()
                if not any(dir_site in domain for dir_site in directories):
                    return url
        
        # Fallback: First result
        if search_results and search_results[0].get('url'):
            return search_results[0]['url']
        
        return None
    
    def _extract_gmb_data(self, search_results: List[Dict]) -> Optional[Dict]:
        """Extract Google My Business data from search results."""
        for result in search_results:
            if result.get('is_gmb') or result.get('source') in ['serper_gmb', 'serper_knowledge']:
                return {
                    'name': result.get('title'),
                    'phone': result.get('phone'),
                    'website': result.get('website'),
                    'rating': result.get('rating'),
                    'type': result.get('type')
                }
        return None
    
    def _extract_contact_info(self, search_results: List[Dict]) -> Dict[str, List[str]]:
        """Extract contact information from search results."""
        contacts = {
            'phones': [],
            'emails': []
        }
        
        for result in search_results:
            # Check for phone in GMB data
            if result.get('phone'):
                contacts['phones'].append(result['phone'])
            
            # Extract from snippets (basic extraction)
            snippet = result.get('snippet', '')
            if snippet:
                # Phone pattern
                import re
                phones = re.findall(r'[\d\s\-\(\)\.]+\d{4}', snippet)
                contacts['phones'].extend(phones[:2])
        
        # Remove duplicates
        contacts['phones'] = list(set(contacts['phones']))[:3]
        
        return contacts
    
    def _extract_from_search_results(self, search_results: List[Dict]) -> Dict:
        """Extract basic data from search results when MCP fails."""
        data = {
            'title': '',
            'description': '',
            'snippets': []
        }
        
        if search_results:
            data['title'] = search_results[0].get('title', '')
            for result in search_results[:3]:
                if result.get('snippet'):
                    data['snippets'].append(result['snippet'])
            data['description'] = ' '.join(data['snippets'])
        
        return data
    
    async def search(self, query: str, **kwargs) -> List[Dict]:
        """
        Search method for compatibility.
        
        Args:
            query: Search query
            **kwargs: Additional arguments
            
        Returns:
            List of search results
        """
        results = await self.serper.search(query, num_results=kwargs.get('max_results', 10))
        formatted = []
        for r in results.get('organic', []):
            formatted.append({
                'title': r.get('title', ''),
                'url': r.get('link', ''),
                'snippet': r.get('snippet', ''),
                'source': 'serper'
            })
        return formatted
    
    async def _scrape_website(self, url: str) -> Dict[str, Any]:
        """
        Scrape website content (for compatibility).
        
        Args:
            url: Website URL
            
        Returns:
            Website content
        """
        try:
            return await self.mcp_extractor.extract(url)
        except Exception as e:
            logger.error(f"Failed to scrape {url}: {e}")
            return {'error': str(e), 'url': url}


# Compatibility function
async def gather_web_data(company_name: str, location: str = "",
                         additional_data: Optional[Dict] = None,
                         campaign_context: Optional[Dict] = None,
                         **kwargs) -> Dict[str, Any]:
    """
    Gather web data using Serper API.
    Drop-in replacement for existing gather_web_data functions.
    """
    async with SerperWebGatherer() as gatherer:
        return await gatherer.search_and_gather(
            company_name=company_name,
            location=location,
            additional_data=additional_data,
            campaign_context=campaign_context
        )


# For direct import compatibility
search_web = search_with_serper