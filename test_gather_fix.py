"""
Test script to verify the gather_web_data function works correctly
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_gather_web_data():
    """Test the gather_web_data wrapper function"""
    try:
        from auto_enrich.web_scraper import gather_web_data
        print("Successfully imported gather_web_data")
        
        # Test with a simple company
        result = await gather_web_data(
            company_name="Miami Motors",
            location="Miami, FL"
        )
        
        print(f"Test successful! Got {len(result)} keys in result")
        print(f"Keys: {list(result.keys())}")
        
        if 'search_results' in result:
            print(f"Found {len(result['search_results'])} search results")
        
        return True
        
    except ImportError as e:
        print(f"Import error: {e}")
        return False
    except Exception as e:
        print(f"Error during test: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_gather_web_data())
    if success:
        print("\nFix verified! The gather_web_data function is working.")
    else:
        print("\nFix failed. Please check the implementation.")