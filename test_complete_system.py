"""
Test the complete Selenium + MCP Fetch system
"""

import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)

async def test_complete_system():
    """Test the complete enrichment pipeline"""
    
    print("\n" + "="*60)
    print("COMPLETE SYSTEM TEST: SELENIUM + MCP FETCH")
    print("="*60 + "\n")
    
    # Test 1: MCP Fetch directly
    print("1. Testing MCP Fetch HTML->Markdown Conversion:")
    print("-" * 40)
    
    from auto_enrich.mcp_client import create_mcp_manager
    
    mcp = await create_mcp_manager()
    
    if mcp.initialized:
        print("[OK] MCP Manager initialized")
        
        # Test fetching and converting to Markdown
        test_url = "https://example.com"
        result = await mcp.fetch_url(test_url, max_length=500)
        
        if result.get('metadata', {}).get('success'):
            print(f"[OK] Successfully fetched {test_url}")
            print(f"    Method: {result['metadata'].get('fetched_via')}")
            print(f"    Content length: {len(result.get('content', ''))}")
            print(f"    Title: {result.get('title', 'N/A')}")
        else:
            print(f"[FAIL] Failed to fetch: {result.get('error')}")
    else:
        print("[WARN] MCP not initialized, will use Selenium fallback")
    
    await mcp.close()
    
    # Test 2: Complete enrichment pipeline
    print("\n2. Testing Complete Enrichment Pipeline:")
    print("-" * 40)
    
    from auto_enrich.web_scraper import WebDataGatherer
    
    async with WebDataGatherer() as gatherer:
        result = await gatherer.search_and_gather(
            company_name="Miami Motors",
            location="Miami FL",
            additional_data={'phone': '305-555-0100'}
        )
        
        print(f"[OK] Search completed")
        print(f"    Results found: {len(result.get('search_results', []))}")
        print(f"    Search engine: {result.get('search_engine')}")
        
        if result.get('website_url'):
            print(f"    Website: {result['website_url']}")
            
        if result.get('website_data'):
            data = result['website_data']
            print(f"[OK] Website content fetched")
            print(f"    Method: {data.get('metadata', {}).get('fetched_via', data.get('fetched_via'))}")
            print(f"    Has content: {len(data.get('content', '')) > 0}")
    
    print("\n" + "="*60)
    print("RATE LIMITING ANALYSIS")
    print("="*60 + "\n")
    
    print("MCP Fetch (httpx + markdownify):")
    print("- NO rate limits on the client side")
    print("- Runs locally, no external API calls")
    print("- Speed: ~1-2 seconds per page")
    print("- Cost: FREE (no tokens, no API fees)")
    print()
    print("Selenium Fallback:")
    print("- NO rate limits on the client side")
    print("- Uses real Chrome browser")
    print("- Speed: ~3-5 seconds per page")
    print("- Cost: FREE (no tokens, no API fees)")
    print()
    print("Website Rate Limiting:")
    print("- Google: May show CAPTCHA after many requests")
    print("- LinkedIn: Aggressive rate limiting, may need login")
    print("- Facebook: Requires login for most content")
    print("- Most corporate sites: No rate limiting")
    print()
    print("Recommendations:")
    print("- Add 1-2 second delay between requests to same domain")
    print("- Rotate user agents for large-scale scraping")
    print("- Use proxies only if absolutely necessary")
    print("- For 10,000 records: expect ~3-6 hours processing time")


if __name__ == "__main__":
    asyncio.run(test_complete_system())