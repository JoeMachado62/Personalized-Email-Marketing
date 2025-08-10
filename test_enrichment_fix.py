"""
Test that the enrichment actually works with the fixed parameters
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_enrichment():
    """Test the complete enrichment flow"""
    try:
        from auto_enrich.web_scraper import gather_web_data
        
        print("Testing enrichment with additional_data parameter...")
        
        # Test with the same parameters that enricher.py uses
        result = await gather_web_data(
            company_name="Test Motors Inc",
            location="Miami, FL",
            additional_data={
                'phone': '305-555-0100',
                'email': 'test@example.com'
            }
        )
        
        print(f"Success! Got {len(result)} keys in result")
        print(f"Keys: {list(result.keys())}")
        
        # Check if we got actual data
        if 'search_results' in result:
            print(f"Found {len(result['search_results'])} search results")
            if result['search_results']:
                print(f"First result: {result['search_results'][0].get('title', 'No title')}")
        
        if 'website_url' in result:
            print(f"Website found: {result['website_url']}")
            
        if 'business_info' in result:
            print(f"Business info keys: {list(result['business_info'].keys())}")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_enrichment())
    if success:
        print("\nEnrichment test successful!")
    else:
        print("\nEnrichment test failed.")