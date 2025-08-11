"""
Serper API client for reliable, fast search results.
Replaces unreliable browser automation with API-based search.
"""

import os
import asyncio
import aiohttp
import logging
from typing import Dict, List, Any, Optional
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)


class SerperClient:
    """
    Client for Serper API - reliable Google search results without browser automation.
    
    Features:
    - Fast API-based search (1-2 seconds)
    - No browser windows or detection issues
    - Rich search results with snippets
    - Support for multiple search types
    - Location-based search
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Serper client.
        
        Args:
            api_key: Serper API key (or set SERPER_API_KEY env variable)
        """
        self.api_key = api_key or os.environ.get('SERPER_API_KEY')
        if not self.api_key:
            logger.warning("No Serper API key found. Set SERPER_API_KEY environment variable.")
        
        self.base_url = "https://google.serper.dev"
        self.headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }
    
    async def search(self, query: str, location: Optional[str] = None, 
                    num_results: int = 10, search_type: str = "search") -> Dict[str, Any]:
        """
        Perform a search using Serper API.
        
        Args:
            query: Search query string
            location: Location for local search (e.g., "Houston, TX")
            num_results: Number of results to return (default 10)
            search_type: Type of search (search, places, images, news, etc.)
            
        Returns:
            Dictionary with search results
        """
        if not self.api_key:
            logger.error("No API key configured for Serper")
            return {'error': 'No API key configured', 'organic': []}
        
        endpoint = f"{self.base_url}/{search_type}"
        
        # Build request payload
        payload = {
            'q': query,
            'num': num_results
        }
        
        # Add location if provided
        if location:
            payload['location'] = location
            payload['gl'] = 'us'  # Country code
            payload['hl'] = 'en'  # Language
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint, json=payload, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"Serper search successful for: {query}")
                        return data
                    else:
                        error_text = await response.text()
                        logger.error(f"Serper API error {response.status}: {error_text}")
                        return {'error': f'API error {response.status}', 'organic': []}
                        
        except Exception as e:
            logger.error(f"Serper request failed: {e}")
            return {'error': str(e), 'organic': []}
    
    async def search_business(self, company_name: str, location: str = "") -> List[Dict[str, Any]]:
        """
        Search for a business with location context.
        
        Args:
            company_name: Name of the business
            location: Business location
            
        Returns:
            List of search results formatted for our system
        """
        # Construct optimized business search query
        if location:
            query = f"{company_name} {location}"
        else:
            query = company_name
        
        # Perform search
        results = await self.search(query, location=location, num_results=10)
        
        # Format results for our system
        formatted_results = []
        
        # Check for local/places results first (Google My Business)
        if 'places' in results:
            for place in results.get('places', [])[:3]:
                formatted_results.append({
                    'title': place.get('title', ''),
                    'url': place.get('link', ''),
                    'snippet': place.get('address', ''),
                    'source': 'serper_gmb',
                    'is_gmb': True,
                    'phone': place.get('phone'),
                    'rating': place.get('rating'),
                    'website': place.get('website')
                })
        
        # Add organic search results
        for result in results.get('organic', []):
            formatted_results.append({
                'title': result.get('title', ''),
                'url': result.get('link', ''),
                'snippet': result.get('snippet', ''),
                'source': 'serper',
                'is_gmb': False
            })
        
        # Check for knowledge graph (company info panel)
        if 'knowledgeGraph' in results:
            kg = results['knowledgeGraph']
            formatted_results.insert(0, {
                'title': kg.get('title', ''),
                'url': kg.get('website', kg.get('link', '')),
                'snippet': kg.get('description', ''),
                'source': 'serper_knowledge',
                'is_gmb': True,
                'website': kg.get('website'),
                'type': kg.get('type')
            })
        
        return formatted_results
    
    async def get_place_details(self, company_name: str, location: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed place/business information using Places search.
        
        Args:
            company_name: Business name
            location: Business location
            
        Returns:
            Place details or None
        """
        query = f"{company_name} {location}"
        results = await self.search(query, location=location, search_type="places")
        
        if results.get('places'):
            place = results['places'][0]
            return {
                'name': place.get('title'),
                'address': place.get('address'),
                'phone': place.get('phone'),
                'website': place.get('link'),
                'rating': place.get('rating'),
                'reviews': place.get('reviews'),
                'hours': place.get('hours'),
                'place_id': place.get('placeId')
            }
        
        return None


class SerperSearchProvider:
    """
    Search provider implementation using Serper API.
    Drop-in replacement for Selenium/Playwright search.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with API key."""
        self.client = SerperClient(api_key)
    
    async def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Generic search method compatible with existing code.
        
        Args:
            query: Search query
            max_results: Maximum results to return
            
        Returns:
            List of search results
        """
        results = await self.client.search(query, num_results=max_results)
        
        formatted = []
        for result in results.get('organic', [])[:max_results]:
            formatted.append({
                'title': result.get('title', ''),
                'url': result.get('link', ''),
                'snippet': result.get('snippet', ''),
                'source': 'serper'
            })
        
        return formatted
    
    async def search_business(self, company_name: str, location: str = "") -> List[Dict[str, Any]]:
        """Search for a business."""
        return await self.client.search_business(company_name, location)


# Compatibility function for existing code
async def search_with_serper(query: str, location: Optional[str] = None, 
                            max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Search using Serper API - drop-in replacement for search_with_selenium.
    
    Args:
        query: Search query
        location: Optional location context
        max_results: Maximum results
        
    Returns:
        List of search results
    """
    client = SerperClient()
    
    # If it looks like a business search, use business search
    if location:
        results = await client.search_business(query, location)
    else:
        results_data = await client.search(query, num_results=max_results)
        results = []
        for r in results_data.get('organic', []):
            results.append({
                'title': r.get('title', ''),
                'url': r.get('link', ''),
                'snippet': r.get('snippet', ''),
                'source': 'serper'
            })
    
    return results[:max_results]


# Test function
async def test_serper():
    """Test Serper API integration."""
    client = SerperClient()
    
    # Test basic search
    print("Testing basic search...")
    results = await client.search("Mike's Auto Shop Houston TX")
    print(f"Found {len(results.get('organic', []))} organic results")
    
    # Test business search
    print("\nTesting business search...")
    business_results = await client.search_business("Mike's Auto Shop", "Houston, TX")
    print(f"Found {len(business_results)} business results")
    
    if business_results:
        print(f"First result: {business_results[0].get('title')} - {business_results[0].get('url')}")
    
    return len(results.get('organic', [])) > 0


if __name__ == "__main__":
    # Test the Serper client
    import asyncio
    asyncio.run(test_serper())