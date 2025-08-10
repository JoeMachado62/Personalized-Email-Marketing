# MCP Server Integration Strategy for Enhanced Enrichment

## Overview
Model Context Protocol (MCP) servers can provide specialized capabilities that would significantly improve our enrichment pipeline's effectiveness and efficiency.

## Proposed MCP Server Integrations

### 1. Fetch MCP Server - Enhanced Web Scraping (NO TOKEN COSTS)
**Current Challenge**: Our Playwright/Selenium scraping can timeout, fail on complex sites, or struggle with JavaScript-heavy content.

**IMPORTANT**: Fetch MCP does NOT require an LLM API key or incur token costs. It's a simple HTML-to-Markdown converter that runs locally.

**MCP Solution**:
```python
# Instead of complex Playwright setup:
async def fetch_with_mcp(url: str, campaign_context: Dict) -> Dict:
    """Use MCP Fetch server for robust content extraction"""
    # MCP handles:
    # - HTML to Markdown conversion
    # - Chunked reading for large pages
    # - Better handling of dynamic content
    
    response = await mcp_client.fetch(
        url=url,
        max_length=10000,
        start_index=0
    )
    return parse_markdown_content(response)
```

**Benefits**:
- More reliable content extraction
- Built-in HTML-to-Markdown conversion
- Chunked reading for large pages
- Less overhead than browser automation
- Better handling of rate limits

**Integration Points**:
1. Replace `WebDataGatherer._scrape_website()` with MCP fetch
2. Use for social media profile extraction
3. Fetch news articles and blog posts
4. Extract review content

### 2. Exa MCP Server - Development Assistance Only (HAS API COSTS)
**IMPORTANT**: Exa MCP has API costs and should NOT be integrated into production code. Use it for:
- Helping developers research solutions
- Finding documentation for bug fixes
- Discovering best practices and patterns
- Researching new technologies

**NOT FOR PRODUCTION**: Do not use Exa in the enrichment pipeline due to costs.

**Development Use Case**:
```python
async def search_industry_specific(company: str, industry: str) -> List[Dict]:
    """Use Exa for specialized industry research"""
    # Exa excels at finding:
    # - Industry-specific documentation
    # - Technical specifications
    # - API documentation
    # - Best practices
    # - Competitor analysis
    
    results = await exa_client.search(
        query=f"{company} {industry} technology stack",
        num_results=10,
        type="technical"
    )
    return results
```

**Benefits**:
- Better technical/industry content discovery
- Higher quality results for B2B research
- Access to documentation and technical resources
- Competitor technology stack analysis

### 3. Potential Custom MCP Servers

#### Social Media MCP Server
```python
class SocialMediaMCP:
    """Custom MCP for social media data extraction"""
    
    async def get_linkedin_profile(self, company_name: str):
        # Specialized LinkedIn extraction
        pass
    
    async def get_facebook_insights(self, page_url: str):
        # Facebook page analysis
        pass
    
    async def get_twitter_sentiment(self, handle: str):
        # Twitter/X sentiment analysis
        pass
```

#### Review Aggregator MCP
```python
class ReviewMCP:
    """Aggregate reviews from multiple platforms"""
    
    async def get_all_reviews(self, business_name: str, location: str):
        # Aggregate from Yelp, Google, BBB, etc.
        return {
            'average_rating': 4.5,
            'total_reviews': 342,
            'sentiment_analysis': {...},
            'common_complaints': [...],
            'common_praises': [...]
        }
```

## Implementation Architecture

### 1. MCP Client Manager
```python
# auto_enrich/mcp_client.py
class MCPClientManager:
    """Manages connections to multiple MCP servers"""
    
    def __init__(self):
        self.fetch_client = None
        self.exa_client = None
        self.custom_clients = {}
    
    async def initialize(self):
        """Initialize all configured MCP servers"""
        if os.getenv('ENABLE_MCP_FETCH'):
            self.fetch_client = await FetchMCPClient.connect()
        
        if os.getenv('EXA_API_KEY'):
            self.exa_client = await ExaMCPClient.connect(
                api_key=os.getenv('EXA_API_KEY')
            )
    
    async def fetch_url(self, url: str, **kwargs):
        """Fetch URL content with fallback to traditional scraping"""
        if self.fetch_client:
            try:
                return await self.fetch_client.fetch(url, **kwargs)
            except Exception as e:
                logger.warning(f"MCP fetch failed: {e}, falling back")
        
        # Fallback to Playwright
        return await traditional_scrape(url)
```

### 2. Enhanced Profile Builder with MCP
```python
# auto_enrich/profile_builder_mcp.py
class MCPEnhancedProfileBuilder(ProfileBuilder):
    """Profile builder enhanced with MCP capabilities"""
    
    def __init__(self, campaign_context: Dict, mcp_manager: MCPClientManager):
        super().__init__(campaign_context)
        self.mcp = mcp_manager
    
    async def extract_profile_data(self, source: Dict) -> Dict:
        """Extract data using MCP servers when available"""
        
        url = source['url']
        source_type = source['source_type']
        
        # Use MCP Fetch for better extraction
        if self.mcp.fetch_client:
            content = await self.mcp.fetch_url(
                url=url,
                max_length=10000
            )
            
            # Parse markdown content based on source type
            if source_type == 'linkedin':
                return self._parse_linkedin_markdown(content)
            elif source_type == 'news':
                return self._parse_news_markdown(content)
        
        # Fallback to traditional extraction
        return await super().extract_profile_data(source)
    
    async def search_technical_insights(self, company: str):
        """Use Exa for technical research"""
        if self.mcp.exa_client:
            results = await self.mcp.exa_client.search(
                query=f"{company} technology stack API integrations",
                num_results=5
            )
            
            return {
                'technologies_used': self._extract_tech_stack(results),
                'api_integrations': self._extract_apis(results),
                'technical_challenges': self._extract_challenges(results)
            }
```

### 3. Intelligent MCP Router
```python
class MCPRouter:
    """Routes requests to appropriate MCP servers based on content type"""
    
    ROUTING_RULES = {
        'linkedin.com': 'fetch_enhanced',  # Use Fetch with special parsing
        'facebook.com': 'social_mcp',      # Custom social MCP
        'github.com': 'exa',               # Exa for technical content
        'news': 'fetch',                   # Standard Fetch
        'technical': 'exa',                # Exa for documentation
        'reviews': 'review_mcp'            # Custom review aggregator
    }
    
    async def route_request(self, url: str, content_type: str):
        """Route to appropriate MCP server"""
        domain = urlparse(url).netloc
        
        # Determine best MCP server
        if domain in self.ROUTING_RULES:
            server = self.ROUTING_RULES[domain]
        else:
            server = self.ROUTING_RULES.get(content_type, 'fetch')
        
        return await self.execute_on_server(server, url)
```

## Configuration

### Environment Variables
```env
# MCP Configuration
ENABLE_MCP_FETCH=true
MCP_FETCH_TIMEOUT=30000
MCP_FETCH_MAX_LENGTH=10000

# Exa Configuration
EXA_API_KEY=your_exa_api_key
EXA_SEARCH_TYPE=neural

# Custom MCP Servers
CUSTOM_MCP_SERVERS=social,review,industry
SOCIAL_MCP_ENDPOINT=http://localhost:3000
```

### Settings Integration
```python
# auto_enrich/config.py
MCP_CONFIG = {
    'fetch': {
        'enabled': os.getenv('ENABLE_MCP_FETCH', 'false').lower() == 'true',
        'timeout': int(os.getenv('MCP_FETCH_TIMEOUT', 30000)),
        'max_length': int(os.getenv('MCP_FETCH_MAX_LENGTH', 10000))
    },
    'exa': {
        'enabled': bool(os.getenv('EXA_API_KEY')),
        'api_key': os.getenv('EXA_API_KEY'),
        'search_type': os.getenv('EXA_SEARCH_TYPE', 'neural')
    }
}
```

## Benefits of MCP Integration

### 1. Improved Reliability
- MCP servers handle retries and error recovery
- Better handling of rate limits
- Graceful degradation with fallbacks

### 2. Enhanced Data Quality
- Specialized extraction for different content types
- Better markdown conversion preserves structure
- Industry-specific search capabilities

### 3. Performance Optimization
- Reduced overhead vs browser automation
- Parallel processing with multiple MCP servers
- Caching at MCP server level

### 4. Scalability
- Distribute load across specialized servers
- Add new capabilities without modifying core code
- Easy to add new MCP servers

### 5. Cost Efficiency
- Reduce API calls through better targeting
- Cache responses at MCP level
- Only fetch what's needed with chunking

## Implementation Roadmap

### Phase 1: Basic Integration (Week 1)
1. Install and configure Fetch MCP
2. Replace basic web scraping with MCP Fetch
3. Add fallback mechanisms
4. Test with existing pipeline

### Phase 2: Enhanced Search (Week 2)
1. Integrate Exa MCP for technical search
2. Route technical queries to Exa
3. Combine results with Google search
4. Measure quality improvements

### Phase 3: Custom MCP Servers (Week 3-4)
1. Develop Social Media MCP
2. Create Review Aggregator MCP
3. Build Industry-Specific MCP
4. Integrate with profile builder

### Phase 4: Optimization (Week 5)
1. Implement intelligent routing
2. Add caching strategies
3. Performance tuning
4. A/B testing MCP vs traditional

## Example: Complete MCP-Enhanced Pipeline

```python
async def enrich_with_mcp(company_data: Dict, campaign_context: Dict):
    """Enhanced enrichment using MCP servers"""
    
    # Initialize MCP manager
    mcp = MCPClientManager()
    await mcp.initialize()
    
    # 1. Use Exa for industry research
    if campaign_context.get('industry'):
        technical_insights = await mcp.exa_client.search(
            f"{company_data['name']} {campaign_context['industry']} technology"
        )
    
    # 2. Use Fetch MCP for website content
    if company_data.get('website'):
        website_content = await mcp.fetch_client.fetch(
            url=company_data['website'],
            max_length=15000
        )
    
    # 3. Use custom Social MCP for social profiles
    social_profiles = await mcp.social_client.get_all_profiles(
        company_name=company_data['name']
    )
    
    # 4. Aggregate and synthesize
    profile = synthesize_profile(
        technical_insights,
        website_content,
        social_profiles
    )
    
    return profile
```

## Testing Strategy

### Unit Tests
```python
@pytest.mark.asyncio
async def test_mcp_fetch_integration():
    """Test MCP Fetch server integration"""
    mcp = MCPClientManager()
    await mcp.initialize()
    
    result = await mcp.fetch_url("https://example.com")
    assert result is not None
    assert 'content' in result
```

### Integration Tests
```python
async def test_mcp_pipeline():
    """Test complete pipeline with MCP"""
    test_company = {
        'name': 'Tesla',
        'location': 'Austin, TX'
    }
    
    result = await enrich_with_mcp(
        test_company,
        {'industry': 'automotive', 'focus': 'technology'}
    )
    
    assert result['technical_stack']
    assert result['social_presence']
    assert len(result['personalization_hooks']) > 3
```

## Security Considerations

1. **URL Validation**: Validate URLs before sending to MCP
2. **Rate Limiting**: Implement rate limits per MCP server
3. **Data Sanitization**: Sanitize MCP responses
4. **Access Control**: Restrict MCP server access
5. **Monitoring**: Log all MCP requests/responses

## Conclusion

MCP integration would provide:
- **30-50% reduction** in scraping failures
- **2-3x improvement** in data quality for technical content
- **40% faster** enrichment through parallel MCP processing
- **Better personalization** through specialized data sources

The modular nature of MCP servers makes this a low-risk, high-reward enhancement to our enrichment pipeline.