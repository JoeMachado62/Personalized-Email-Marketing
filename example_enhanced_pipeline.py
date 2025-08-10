"""
Example script demonstrating the enhanced enrichment pipeline.

This script shows how to use the new worker system with the existing
auto_enrich modules to process dealership data at scale.
"""

import asyncio
import logging
from pathlib import Path
from app.services import get_job_service, get_scraper_service, get_cache_service, ScrapingConfig
from app.workers import get_enrichment_worker
from app.models.job import JobCreate

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Example of using the enhanced enrichment pipeline."""
    
    logger.info("Starting enhanced enrichment pipeline example")
    
    # Configure scraping with production-ready settings
    scraping_config = ScrapingConfig(
        max_retries=3,
        retry_delay_base=1.0,
        retry_delay_max=10.0,
        concurrent_limit=3,
        use_cache=True,
        cache_ttl_hours=24,
        timeout_ms=30000
    )
    
    # Initialize services
    job_service = get_job_service()
    scraper_service = get_scraper_service(scraping_config)
    cache_service = get_cache_service()
    
    # Initialize worker
    worker = get_enrichment_worker(
        max_concurrent_jobs=1,
        max_concurrent_records=3,
        scraping_config=scraping_config
    )
    
    # Example: Create a job (assuming you have a CSV file)
    input_file = "data/sample_dealers.csv"
    
    if Path(input_file).exists():
        try:
            # Create job
            job_create = JobCreate(options={
                "include_contact_extraction": True,
                "cache_results": True,
                "max_retries": 3
            })
            
            job_response = await job_service.create_job(input_file, job_create)
            logger.info(f"Created job: {job_response.job_id}")
            
            # Start worker in background
            worker_task = asyncio.create_task(worker.start())
            
            # Monitor job progress
            job_id = job_response.job_id
            while True:
                status = await job_service.get_job_status(job_id)
                if status:
                    logger.info(f"Job {job_id} status: {status.status}, "
                               f"progress: {status.progress.percentage}%")
                    
                    if status.status in ["completed", "failed", "cancelled"]:
                        break
                
                await asyncio.sleep(10)  # Check every 10 seconds
            
            # Stop worker
            await worker.stop()
            worker_task.cancel()
            
            # Show final results
            final_status = await job_service.get_job_status(job_id)
            if final_status:
                logger.info(f"Final status: {final_status.status}")
                logger.info(f"Processed: {final_status.progress.processed_records}")
                logger.info(f"Failed: {final_status.progress.failed_records}")
                logger.info(f"Actual cost: ${final_status.actual_cost:.2f}")
            
            # Show cache statistics
            cache_stats = cache_service.get_stats()
            logger.info(f"Cache hits: {cache_stats['hits']}, "
                       f"hit rate: {cache_stats['hit_rate_percent']}%")
            logger.info(f"Cost saved by caching: ${cache_stats['cost_saved']:.2f}")
            
        except Exception as e:
            logger.error(f"Error processing job: {e}")
            import traceback
            logger.error(traceback.format_exc())
    else:
        logger.warning(f"Input file {input_file} not found. Creating sample data...")
        
        # Create sample CSV for demonstration
        import pandas as pd
        sample_data = {
            "Dealer": ["ABC Auto", "Best Cars LLC", "Quality Motors"],
            "Address": ["123 Main St, Anytown, NY 12345", 
                       "456 Oak Ave, Somewhere, CA 90210",
                       "789 Pine Rd, Elsewhere, TX 75001"],
            "Phone": ["555-0123", "555-0456", "555-0789"],
            "Email": ["info@abcauto.com", "sales@bestcars.com", "contact@qualitymotors.com"]
        }
        
        df = pd.DataFrame(sample_data)
        Path("data").mkdir(exist_ok=True)
        df.to_csv(input_file, index=False)
        logger.info(f"Created sample file: {input_file}")
        logger.info("Run the script again to process the sample data")


async def test_individual_services():
    """Test individual services to verify integration."""
    
    logger.info("Testing individual services...")
    
    # Test cache service
    cache_service = get_cache_service()
    await cache_service.set("test", {"param": "value"}, "test_result")
    cached_result = await cache_service.get("test", {"param": "value"})
    logger.info(f"Cache test result: {cached_result}")
    
    # Test scraper service
    scraper_service = get_scraper_service()
    health = await scraper_service.health_check()
    logger.info(f"Scraper service health: {health['status']}")
    
    # Test a simple website search (this will use the existing auto_enrich module)
    result = await scraper_service.find_dealer_website_enhanced("ABC Auto", "New York")
    logger.info(f"Website search result: success={result.success}, website={result.website}")
    
    logger.info("Service tests completed")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test-services":
        asyncio.run(test_individual_services())
    else:
        asyncio.run(main())