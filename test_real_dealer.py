"""
Test with actual dealer from the CSV
"""
import asyncio
import logging
import sys
from pathlib import Path
import pandas as pd

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_real_dealer():
    """Test enriching a real dealer from the CSV"""
    
    try:
        # Import after path is set
        from auto_enrich.web_scraper import gather_web_data
        from auto_enrich.data_interpreter import interpret_scraped_data
        
        # Load actual data from CSV
        df = pd.read_csv('uploads/6c498e99-60c2-4e2b-a2ec-d76cf345c65e.csv')
        
        # Test with first dealer
        dealer = df.iloc[0]
        test_company = dealer['DEALER NAME']
        test_location = f"{dealer['LOCATION CITY']}, {dealer['STATE']}"
        test_phone = dealer['PHONE']
        
        logger.info(f"Testing with REAL dealer: {test_company}")
        logger.info(f"Location: {test_location}")
        logger.info(f"Phone: {test_phone}")
        
        # Step 1: Gather web data
        logger.info("Step 1: Gathering web data...")
        scraped_data = await gather_web_data(
            company_name=test_company,
            location=test_location,
            additional_data={'phone': test_phone}
        )
        
        logger.info(f"Search results found: {len(scraped_data.get('search_results', []))}")
        if scraped_data.get('search_results'):
            for i, result in enumerate(scraped_data['search_results'][:3]):
                logger.info(f"  Result {i+1}: {result.get('title', 'No title')}")
                logger.info(f"    URL: {result.get('url', 'No URL')}")
        
        logger.info(f"Website found: {scraped_data.get('website_url', 'None')}")
        
        if scraped_data.get('error'):
            logger.error(f"Scraping error: {scraped_data['error']}")
            return
        
        # Only proceed if we have data
        if scraped_data.get('search_results') or scraped_data.get('website_url'):
            # Step 2: Interpret with AI
            logger.info("Step 2: Interpreting with AI...")
            interpreted_data = await interpret_scraped_data(scraped_data)
            
            logger.info(f"Extracted owner info: {interpreted_data.get('extracted_info', {}).get('owner', {})}")
            logger.info(f"Business details: {interpreted_data.get('extracted_info', {}).get('business_details', {})}")
            
            # Check email content
            email_content = interpreted_data.get('generated_content', {})
            if email_content:
                subject = email_content.get('subject', {}).get('raw_response', '')
                logger.info(f"Generated subject: {subject}")
            
            return interpreted_data
        else:
            logger.warning("No search results or website found - cannot enrich")
            return None
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return None

if __name__ == "__main__":
    result = asyncio.run(test_real_dealer())
    if result and result.get('extracted_info'):
        print("\nEnrichment test successful!")
        print(f"Found data for: {result.get('company_name')}")
    else:
        print("\nEnrichment test failed - no data found")