"""
MCP Client Manager - Integrates Model Context Protocol servers for enhanced data collection
"""

import os
import logging
import json
import asyncio
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse
import subprocess

logger = logging.getLogger(__name__)


class MCPClientManager:
    """
    Manages connections to multiple MCP servers for enhanced enrichment capabilities.
    Provides fallback mechanisms to ensure reliability.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize MCP client manager with configuration.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or self._load_config()
        self.fetch_client = None
        self.exa_client = None
        self.custom_clients = {}
        self.initialized = False
    
    def _load_config(self) -> Dict[str, Any]:
        """Load MCP configuration from environment variables"""
        return {
            'fetch': {
                'enabled': os.getenv('ENABLE_MCP_FETCH', 'false').lower() == 'true',
                'command': os.getenv('MCP_FETCH_COMMAND', 'python -m mcp_server_fetch'),
                'timeout': int(os.getenv('MCP_FETCH_TIMEOUT', 30000)),
                'max_length': int(os.getenv('MCP_FETCH_MAX_LENGTH', 10000))
            },
            'exa': {
                'enabled': bool(os.getenv('EXA_API_KEY')),
                'api_key': os.getenv('EXA_API_KEY'),
                'command': 'npx -y exa-mcp-server',
                'search_type': os.getenv('EXA_SEARCH_TYPE', 'neural')
            }
        }
    
    async def initialize(self) -> bool:
        """
        Initialize all configured MCP servers.
        
        Returns:
            True if at least one MCP server initialized successfully
        """
        success_count = 0
        
        # Initialize Fetch MCP if enabled
        if self.config['fetch']['enabled']:
            try:
                self.fetch_client = await self._init_fetch_mcp()
                logger.info("Fetch MCP server initialized successfully")
                success_count += 1
            except Exception as e:
                logger.warning(f"Failed to initialize Fetch MCP: {e}")
        
        # Initialize Exa MCP if API key provided
        if self.config['exa']['enabled']:
            try:
                self.exa_client = await self._init_exa_mcp()
                logger.info("Exa MCP server initialized successfully")
                success_count += 1
            except Exception as e:
                logger.warning(f"Failed to initialize Exa MCP: {e}")
        
        self.initialized = success_count > 0
        return self.initialized
    
    async def _init_fetch_mcp(self) -> 'FetchMCPClient':
        """Initialize Fetch MCP server"""
        return FetchMCPClient(self.config['fetch'])
    
    async def _init_exa_mcp(self) -> 'ExaMCPClient':
        """Initialize Exa MCP server"""
        return ExaMCPClient(self.config['exa'])
    
    async def fetch_url(self, url: str, max_length: Optional[int] = None, 
                       start_index: int = 0, raw: bool = False) -> Dict[str, Any]:
        """
        Fetch URL content - prioritize FREE Fetch MCP, fallback to Selenium if needed.
        
        NOTE: Fetch MCP has NO token costs - it's just HTML to Markdown conversion.
        We should use it as primary method when available.
        
        Args:
            url: URL to fetch
            max_length: Maximum characters to return
            start_index: Start content from this index
            raw: Get raw content without markdown conversion
            
        Returns:
            Fetched content dictionary
        """
        # Try MCP Fetch first (NO COST - just HTML conversion)
        if self.fetch_client:
            try:
                logger.info(f"Using FREE Fetch MCP for {url}")
                return await self.fetch_client.fetch(
                    url=url,
                    max_length=max_length or self.config['fetch']['max_length'],
                    start_index=start_index,
                    raw=raw
                )
            except Exception as e:
                logger.warning(f"MCP fetch failed for {url}: {e}, using Selenium fallback")
        
        # Fallback to Selenium/Playwright
        from .web_scraper import WebDataGatherer
        
        logger.info(f"Using Selenium fallback for {url}")
        async with WebDataGatherer() as gatherer:
            return await gatherer._scrape_website(url)
    
    async def search_technical_development_only(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        """
        DEVELOPMENT USE ONLY - Search for technical/documentation content using Exa MCP.
        
        WARNING: This method has API costs and should NOT be used in production enrichment.
        Use it only for development assistance, bug research, and finding documentation.
        
        Args:
            query: Search query for development/documentation
            num_results: Number of results to return
            
        Returns:
            List of search results
        """
        logger.warning("Using Exa MCP - this has API costs and should only be used for development!")
        
        if self.exa_client:
            try:
                return await self.exa_client.search(
                    query=query,
                    num_results=num_results
                )
            except Exception as e:
                logger.warning(f"Exa search failed: {e}, using free Google fallback")
        
        # Fallback to free Google search
        from .search_with_selenium import search_with_real_chrome
        
        logger.info(f"Using free Google search instead: {query}")
        return search_with_real_chrome(query, headless=True)
    
    async def fetch_in_chunks(self, url: str, chunk_size: int = 5000) -> str:
        """
        Fetch large content in chunks using MCP.
        
        Args:
            url: URL to fetch
            chunk_size: Size of each chunk
            
        Returns:
            Complete content
        """
        if not self.fetch_client:
            # Fallback to single fetch
            result = await self.fetch_url(url)
            return result.get('content', '')
        
        full_content = []
        start_index = 0
        
        while True:
            try:
                chunk = await self.fetch_client.fetch(
                    url=url,
                    max_length=chunk_size,
                    start_index=start_index
                )
                
                if not chunk or not chunk.get('content'):
                    break
                
                full_content.append(chunk['content'])
                
                # Check if we've reached the end
                if len(chunk['content']) < chunk_size:
                    break
                
                start_index += chunk_size
                
            except Exception as e:
                logger.error(f"Error fetching chunk at index {start_index}: {e}")
                break
        
        return ''.join(full_content)
    
    async def close(self):
        """Close all MCP client connections"""
        if self.fetch_client:
            await self.fetch_client.close()
        if self.exa_client:
            await self.exa_client.close()
        for client in self.custom_clients.values():
            await client.close()


class FetchMCPClient:
    """
    Client for Fetch MCP server - uses httpx + markdownify for HTML to Markdown conversion.
    This provides the same functionality as MCP Fetch server but with direct Python implementation.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.process = None
    
    async def fetch(self, url: str, max_length: int = 5000, 
                   start_index: int = 0, raw: bool = False) -> Dict[str, Any]:
        """
        Fetch content from URL and convert to Markdown.
        
        This uses httpx for fetching and markdownify for HTML->Markdown conversion,
        which is exactly what MCP Fetch server does internally.
        
        Rate Limiting: None from this client. Individual websites may rate limit.
        """
        try:
            import httpx
            from markdownify import markdownify as md
            from bs4 import BeautifulSoup
            
            logger.info(f"Fetching {url} (converting to Markdown)")
            
            async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
                # Add headers to look like a real browser
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                
                if raw:
                    # Return raw HTML
                    content = response.text[start_index:start_index + max_length]
                    return {
                        'url': url,
                        'content': content,
                        'metadata': {
                            'fetched_via': 'mcp_fetch_raw',
                            'success': True
                        }
                    }
                else:
                    # Parse and convert to Markdown
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Remove script and style elements
                    for script in soup(["script", "style", "meta", "link"]):
                        script.decompose()
                    
                    # Get title
                    title = soup.title.string if soup.title else ''
                    
                    # Convert to markdown
                    markdown = md(str(soup), heading_style="ATX", strip=['a'])
                    
                    # Apply start_index and max_length
                    if start_index > 0:
                        markdown = markdown[start_index:]
                    if len(markdown) > max_length:
                        markdown = markdown[:max_length] + "..."
                    
                    logger.info(f"Converted {len(response.text)} chars HTML to {len(markdown)} chars Markdown")
                    
                    return {
                        'url': url,
                        'content': markdown,
                        'title': title,
                        'metadata': {
                            'fetched_via': 'mcp_fetch_markdown',
                            'success': True,
                            'original_length': len(response.text),
                            'markdown_length': len(markdown)
                        }
                    }
                    
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP error fetching {url}: {e.response.status_code}")
            return {
                'url': url,
                'content': '',
                'error': f"HTTP {e.response.status_code}",
                'metadata': {'fetched_via': 'mcp_fetch_failed', 'success': False}
            }
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return {
                'url': url,
                'content': '',
                'error': str(e),
                'metadata': {'fetched_via': 'mcp_fetch_failed', 'success': False}
            }
    
    async def close(self):
        """Close MCP server connection"""
        if self.process:
            self.process.terminate()


class ExaMCPClient:
    """
    Client for Exa MCP server - DEVELOPMENT USE ONLY
    
    WARNING: Exa has API costs. Use only for development assistance:
    - Researching bug fixes
    - Finding documentation
    - Learning best practices
    
    DO NOT use in production enrichment pipeline!
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = config.get('api_key')
        if self.api_key:
            logger.warning("Exa MCP configured - remember this has API costs! Use for development only.")
    
    async def search(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        """
        DEVELOPMENT ONLY - Search using Exa for technical/documentation content.
        
        WARNING: This incurs API costs! Use sparingly and only for development.
        
        This is a simplified implementation - in production, you would:
        1. Start the Exa MCP server with API key
        2. Send search request
        3. Parse results
        """
        logger.warning(f"[COSTS] Exa Search: {query} (num_results={num_results})")
        
        # Mock implementation
        return [
            {
                'title': f"[DEV ONLY] Technical result for: {query}",
                'url': 'https://docs.example.com',
                'snippet': 'Technical documentation and API references...',
                'source': 'exa_mcp',
                'warning': 'This result from Exa MCP - has API costs'
            }
        ]
    
    async def close(self):
        """Close Exa MCP connection"""
        pass


class MCPRouter:
    """
    Intelligent router that directs requests to appropriate MCP servers
    based on content type and URL patterns.
    """
    
    def __init__(self, mcp_manager: MCPClientManager):
        self.mcp = mcp_manager
        self.routing_rules = {
            # Domain-based routing
            'linkedin.com': self._fetch_linkedin,
            'facebook.com': self._fetch_facebook,
            'github.com': self._search_technical,
            'stackoverflow.com': self._search_technical,
            
            # Content-type routing
            'news': self._fetch_standard,
            'technical': self._search_technical,
            'social': self._fetch_social,
            'review': self._fetch_reviews
        }
    
    async def route(self, url: str, content_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Route request to appropriate MCP server.
        
        Args:
            url: URL to process
            content_type: Optional content type hint
            
        Returns:
            Processed content
        """
        domain = urlparse(url).netloc.lower()
        
        # Check domain-based routing first
        for pattern, handler in self.routing_rules.items():
            if pattern in domain:
                return await handler(url)
        
        # Fall back to content-type routing
        if content_type and content_type in self.routing_rules:
            handler = self.routing_rules[content_type]
            return await handler(url)
        
        # Default to standard fetch
        return await self._fetch_standard(url)
    
    async def _fetch_standard(self, url: str) -> Dict[str, Any]:
        """Standard fetch using MCP"""
        return await self.mcp.fetch_url(url)
    
    async def _fetch_linkedin(self, url: str) -> Dict[str, Any]:
        """Specialized LinkedIn extraction"""
        content = await self.mcp.fetch_url(url, max_length=15000)
        # Add LinkedIn-specific parsing
        content['parsed_type'] = 'linkedin_profile'
        return content
    
    async def _fetch_facebook(self, url: str) -> Dict[str, Any]:
        """Specialized Facebook extraction"""
        content = await self.mcp.fetch_url(url, max_length=10000)
        content['parsed_type'] = 'facebook_page'
        return content
    
    async def _search_technical(self, url: str) -> Dict[str, Any]:
        """Use Exa for technical content"""
        # Extract relevant search terms from URL
        domain = urlparse(url).netloc
        path = urlparse(url).path
        query = f"site:{domain} {path.replace('/', ' ')}"
        
        results = await self.mcp.search_technical(query, num_results=5)
        return {
            'url': url,
            'technical_results': results,
            'parsed_type': 'technical_documentation'
        }
    
    async def _fetch_social(self, url: str) -> Dict[str, Any]:
        """Fetch social media content"""
        content = await self.mcp.fetch_url(url, max_length=8000)
        content['parsed_type'] = 'social_media'
        return content
    
    async def _fetch_reviews(self, url: str) -> Dict[str, Any]:
        """Fetch review content"""
        content = await self.mcp.fetch_url(url, max_length=12000)
        content['parsed_type'] = 'reviews'
        return content


# Integration helper for existing pipeline
async def create_mcp_manager() -> MCPClientManager:
    """
    Create and initialize MCP manager for use in enrichment pipeline.
    """
    manager = MCPClientManager()
    
    if await manager.initialize():
        logger.info(f"MCP manager initialized with {len([c for c in [manager.fetch_client, manager.exa_client] if c])} servers")
    else:
        logger.warning("No MCP servers available, using traditional methods")
    
    return manager


# Example usage in enrichment pipeline
async def enrich_with_mcp(company_data: Dict[str, Any], 
                          campaign_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhanced enrichment using MCP servers.
    
    Args:
        company_data: Company information to enrich
        campaign_context: Campaign goals and context
        
    Returns:
        Enriched company profile
    """
    # Initialize MCP manager
    mcp = await create_mcp_manager()
    router = MCPRouter(mcp)
    
    try:
        enriched_data = {
            'company': company_data,
            'mcp_sources': []
        }
        
        # Fetch company website with MCP
        if company_data.get('website'):
            website_content = await router.route(
                company_data['website'],
                content_type='corporate'
            )
            enriched_data['website_content'] = website_content
            enriched_data['mcp_sources'].append('website')
        
        # Search for technical insights if B2B
        if campaign_context.get('b2b_focus'):
            tech_query = f"{company_data['name']} technology stack API integrations"
            tech_results = await mcp.search_technical(tech_query)
            enriched_data['technical_insights'] = tech_results
            enriched_data['mcp_sources'].append('technical')
        
        # Fetch social profiles
        social_urls = company_data.get('social_profiles', [])
        for social_url in social_urls:
            social_content = await router.route(social_url, 'social')
            enriched_data[f'social_{urlparse(social_url).netloc}'] = social_content
            enriched_data['mcp_sources'].append(f'social_{urlparse(social_url).netloc}')
        
        logger.info(f"Enriched using {len(enriched_data['mcp_sources'])} MCP sources")
        
        return enriched_data
        
    finally:
        await mcp.close()


if __name__ == "__main__":
    # Test MCP integration
    async def test():
        mcp = await create_mcp_manager()
        
        # Test fetch
        result = await mcp.fetch_url("https://example.com")
        print(f"Fetch result: {result}")
        
        # Test search
        results = await mcp.search_technical("Python MCP server implementation")
        print(f"Search results: {results}")
        
        await mcp.close()
    
    asyncio.run(test())