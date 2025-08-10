"""
Test script to verify Selenium + MCP Fetch integration works properly
"""

import asyncio
import logging
from auto_enrich.web_scraper import WebDataGatherer

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_selenium_mcp():
    """Test the Selenium + MCP Fetch pipeline"""
    
    print("\n=== Testing Selenium + MCP Fetch Integration ===\n")
    
    # Test company
    company_name = "Miami Motors"
    location = "Miami FL"
    
    print(f"Testing with: {company_name} in {location}")
    print("-" * 50)
    
    try:
        # Use the WebDataGatherer (should use Selenium + MCP now)
        async with WebDataGatherer() as gatherer:
            print("\n1. Searching with Selenium...")
            
            result = await gatherer.search_and_gather(
                company_name=company_name,
                location=location,
                additional_data={'phone': '305-555-0100'},
                campaign_context={
                    'industry_keywords': ['auto', 'dealer', 'cars'],
                    'value_proposition': 'Inventory management software'
                }
            )
            
            print("\n2. Search Results:")
            print(f"   - Found {len(result.get('search_results', []))} search results")
            print(f"   - Search engine: {result.get('search_engine', 'unknown')}")
            
            if result.get('website_url'):
                print(f"\n3. Identified Website: {result['website_url']}")
                
            if result.get('website_data'):
                print(f"\n4. Website Data Fetched:")
                print(f"   - Method: {result['website_data'].get('fetched_via', 'unknown')}")
                print(f"   - Title: {result['website_data'].get('title', 'N/A')}")
                
            if result.get('error'):
                print(f"\n❌ Error: {result['error']}")
            else:
                print(f"\n✅ Success! Gathered data for {company_name}")
                
            # Display key findings
            print("\n5. Key Findings:")
            for key in ['company_name', 'location', 'search_engine']:
                if key in result:
                    print(f"   - {key}: {result[key]}")
                    
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        

async def test_mcp_direct():
    """Test MCP Fetch server directly"""
    
    print("\n\n=== Testing MCP Fetch Server Directly ===\n")
    
    try:
        from auto_enrich.mcp_client import create_mcp_manager
        
        mcp = await create_mcp_manager()
        
        if mcp.initialized:
            print("✅ MCP Manager initialized successfully")
            
            # Test fetching a simple URL
            test_url = "https://example.com"
            print(f"\nFetching {test_url}...")
            
            result = await mcp.fetch_url(test_url)
            print(f"Result: {result}")
            
        else:
            print("❌ MCP Manager failed to initialize")
            print("   - MCP Fetch may not be properly configured")
            print("   - Check ENABLE_MCP_FETCH=true in .env")
            
        await mcp.close()
        
    except Exception as e:
        print(f"❌ MCP test failed: {e}")
        

if __name__ == "__main__":
    print("\n" + "="*60)
    print("SELENIUM + MCP FETCH INTEGRATION TEST")
    print("="*60)
    
    # Run tests
    asyncio.run(test_selenium_mcp())
    asyncio.run(test_mcp_direct())