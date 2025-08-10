"""
Test with a known major dealer that definitely has web presence
"""
import asyncio
import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project to path  
sys.path.insert(0, str(Path(__file__).parent))

async def test_known_dealer():
    """Test with a major dealer that definitely exists online"""
    
    try:
        from auto_enrich.web_scraper import gather_web_data
        from auto_enrich.data_interpreter import interpret_scraped_data
        
        # Test with a major dealer chain
        test_company = "AutoNation Ford Miami"
        test_location = "Miami, FL"
        
        logger.info(f"Testing with KNOWN major dealer: {test_company}")
        logger.info(f"Location: {test_location}")
        
        # Step 1: Gather web data
        logger.info("Step 1: Gathering web data...")
        scraped_data = await gather_web_data(
            company_name=test_company,
            location=test_location,
            additional_data={'phone': '305-555-0000'}
        )
        
        logger.info(f"Search results found: {len(scraped_data.get('search_results', []))}")
        if scraped_data.get('search_results'):
            for i, result in enumerate(scraped_data['search_results'][:3]):
                logger.info(f"  Result {i+1}: {result.get('title', 'No title')}")
                logger.info(f"    URL: {result.get('url', 'No URL')}")
        
        logger.info(f"Website found: {scraped_data.get('website_url', 'None')}")
        
        if scraped_data.get('search_results') or scraped_data.get('website_url'):
            # Step 2: Interpret with AI
            logger.info("Step 2: Interpreting with AI...")
            interpreted_data = await interpret_scraped_data(scraped_data)
            
            logger.info(f"Extracted owner info: {interpreted_data.get('extracted_info', {}).get('owner', {})}")
            
            # Check email content
            email_content = interpreted_data.get('generated_content', {})
            if email_content:
                subject = email_content.get('subject', {}).get('raw_response', '')
                logger.info(f"Generated subject: {subject}")
            
            return interpreted_data
        else:
            logger.warning("No results found even for major dealer!")
            return None
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return None

if __name__ == "__main__":
    result = asyncio.run(test_known_dealer())
    if result and result.get('extracted_info'):
        print("\nSUCCESS! Enrichment working for known dealer!")
        print(f"Found data for: {result.get('company_name')}")
    else:
        print("\nFAILED - Even major dealer not working!")