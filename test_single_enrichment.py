"""
Test script to debug single record enrichment
"""
import asyncio
import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_single_enrichment():
    """Test enriching a single dealer record"""
    
    try:
        # Import after path is set
        from auto_enrich.web_scraper import gather_web_data
        from auto_enrich.data_interpreter import interpret_scraped_data
        
        # Test with a single dealer
        test_company = "Bob's Used Cars"
        test_location = "Miami, FL"
        
        logger.info(f"Testing enrichment for: {test_company} in {test_location}")
        
        # Step 1: Gather web data
        logger.info("Step 1: Gathering web data...")
        scraped_data = await gather_web_data(
            company_name=test_company,
            location=test_location,
            additional_data={'phone': '305-555-1234'}
        )
        
        logger.info(f"Scraped data keys: {scraped_data.keys()}")
        logger.info(f"Search results found: {len(scraped_data.get('search_results', []))}")
        logger.info(f"Website found: {scraped_data.get('website_url', 'None')}")
        
        if scraped_data.get('error'):
            logger.error(f"Scraping error: {scraped_data['error']}")
            return
        
        # Step 2: Interpret with AI
        logger.info("Step 2: Interpreting with AI...")
        interpreted_data = await interpret_scraped_data(scraped_data)
        
        logger.info(f"Interpreted data keys: {interpreted_data.keys()}")
        logger.info(f"Extracted info: {interpreted_data.get('extracted_info', {})}")
        logger.info(f"Generated content: {interpreted_data.get('generated_content', {})}")
        
        if interpreted_data.get('error'):
            logger.error(f"Interpretation error: {interpreted_data['error']}")
            return
            
        logger.info("SUCCESS: Enrichment completed!")
        return interpreted_data
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error("Make sure all dependencies are installed")
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return None

if __name__ == "__main__":
    result = asyncio.run(test_single_enrichment())
    if result:
        print("\n✅ Enrichment test successful!")
    else:
        print("\n❌ Enrichment test failed!")