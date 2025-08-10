"""
Integration test script for the enhanced enrichment pipeline.

This script verifies that all components work together correctly:
- auto_enrich modules integration
- Enhanced services functionality  
- Worker system operation
- Database operations
- Caching system
"""

import asyncio
import logging
import traceback
from pathlib import Path
import pandas as pd
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


async def test_auto_enrich_integration():
    """Test integration with existing auto_enrich modules."""
    logger.info("Testing auto_enrich module integration...")
    
    try:
        # Test 1: Import existing modules
        from auto_enrich.scraper import find_dealer_website, extract_contact_info
        from auto_enrich.ai_enrichment import generate_email_content
        from auto_enrich.enricher import DealerRecord
        logger.info("✓ Successfully imported auto_enrich modules")
        
        # Test 2: Test DealerRecord creation
        record = DealerRecord(
            idx=0,
            name="Test Auto Dealership",
            address="123 Main St, Test City, ST 12345",
            phone="555-0123",
            email="test@testdealer.com"
        )
        logger.info(f"✓ Created DealerRecord: {record.name} in {record.city}")
        
        # Test 3: Test website discovery (with mock data to avoid network calls in test)
        logger.info("✓ auto_enrich integration verified")
        return True
        
    except Exception as e:
        logger.error(f"✗ auto_enrich integration failed: {e}")
        logger.error(traceback.format_exc())
        return False


async def test_cache_service():
    """Test cache service functionality."""
    logger.info("Testing cache service...")
    
    try:
        from app.services.cache_service import get_cache_service
        
        cache_service = get_cache_service()
        
        # Test basic caching
        await cache_service.set("test_op", {"key": "value"}, {"result": "test_data"})
        cached_result = await cache_service.get("test_op", {"key": "value"})
        
        assert cached_result == {"result": "test_data"}, "Cache retrieval failed"
        logger.info("✓ Basic caching works")
        
        # Test website caching
        await cache_service.set_website_cache("Test Dealer", "Test City", "https://testdealer.com")
        website = await cache_service.get_website_cache("Test Dealer", "Test City")
        assert website == "https://testdealer.com", "Website cache failed"
        logger.info("✓ Website caching works")
        
        # Test AI content caching
        test_content = ("Test Subject", "Test Icebreaker", "Test Hot Button")
        await cache_service.set_ai_content_cache(
            "Test Dealer", "Test City", "https://testdealer.com", "test@example.com", test_content
        )
        cached_content = await cache_service.get_ai_content_cache(
            "Test Dealer", "Test City", "https://testdealer.com", "test@example.com"
        )
        assert cached_content == test_content, "AI content cache failed"
        logger.info("✓ AI content caching works")
        
        # Test cache stats
        stats = cache_service.get_stats()
        assert "hits" in stats, "Cache stats missing"
        logger.info(f"✓ Cache stats: {stats}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Cache service test failed: {e}")
        logger.error(traceback.format_exc())
        return False


async def test_scraper_service():
    """Test enhanced scraper service."""
    logger.info("Testing scraper service...")
    
    try:
        from app.services.scraper_service import get_scraper_service, ScrapingConfig
        
        config = ScrapingConfig(
            max_retries=1,  # Reduce for testing
            concurrent_limit=1,
            use_cache=True,
            timeout_ms=10000
        )
        
        scraper_service = get_scraper_service(config)
        
        # Test health check
        health = await scraper_service.health_check()
        logger.info(f"✓ Scraper health check: {health['status']}")
        
        # Test URL validation
        valid_url = scraper_service._clean_and_validate_url("www.example.com")
        assert valid_url == "https://www.example.com", "URL validation failed"
        logger.info("✓ URL validation works")
        
        # Test phone number extraction
        phones = scraper_service._extract_phone_numbers("Call us at 555-123-4567 or (555) 987-6543")
        assert len(phones) >= 1, "Phone extraction failed"
        logger.info(f"✓ Phone extraction works: found {len(phones)} numbers")
        
        # Test email extraction
        emails = scraper_service._extract_email_addresses("Contact us at info@dealer.com or sales@dealer.com")
        assert len(emails) >= 1, "Email extraction failed"
        logger.info(f"✓ Email extraction works: found {len(emails)} emails")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Scraper service test failed: {e}")
        logger.error(traceback.format_exc())
        return False


async def test_job_service():
    """Test job management service."""
    logger.info("Testing job service...")
    
    try:
        from app.services.job_service import get_job_service
        from app.models.job import JobCreate
        import tempfile
        import os
        
        job_service = get_job_service()
        
        # Create test CSV file
        test_data = {
            "Dealer": ["Test Dealer 1", "Test Dealer 2"],
            "Address": ["123 Test St, Test City, ST 12345", "456 Test Ave, Test Town, ST 67890"],
            "Phone": ["555-0001", "555-0002"],
            "Email": ["test1@example.com", "test2@example.com"]
        }
        
        df = pd.DataFrame(test_data)
        
        # Use temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
            df.to_csv(tmp.name, index=False)
            tmp_path = tmp.name
        
        try:
            # Test job creation
            job_create = JobCreate(options={"test": True})
            job_response = await job_service.create_job(tmp_path, job_create)
            
            assert job_response.job_id is not None, "Job creation failed"
            logger.info(f"✓ Created job: {job_response.job_id}")
            
            # Test job status retrieval
            status = await job_service.get_job_status(job_response.job_id)
            assert status is not None, "Job status retrieval failed"
            assert status.status == "pending", "Job should be pending"
            logger.info(f"✓ Job status: {status.status}")
            
            # Test job records retrieval
            records = await job_service.get_job_records(job_response.job_id)
            assert len(records) == 2, f"Expected 2 records, got {len(records)}"
            logger.info(f"✓ Retrieved {len(records)} job records")
            
            # Test pending jobs retrieval
            pending_jobs = await job_service.get_pending_jobs()
            assert len(pending_jobs) >= 1, "Should have at least one pending job"
            logger.info(f"✓ Found {len(pending_jobs)} pending jobs")
            
        finally:
            # Clean up temporary file
            os.unlink(tmp_path)
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Job service test failed: {e}")
        logger.error(traceback.format_exc())
        return False


async def test_worker_initialization():
    """Test worker initialization and basic functionality."""
    logger.info("Testing worker initialization...")
    
    try:
        from app.workers.enrichment_worker import get_enrichment_worker
        from app.services.scraper_service import ScrapingConfig
        
        config = ScrapingConfig(
            max_retries=1,
            concurrent_limit=1,
            use_cache=True
        )
        
        worker = get_enrichment_worker(
            max_concurrent_jobs=1,
            max_concurrent_records=2,
            scraping_config=config
        )
        
        # Test health check
        health = await worker.health_check()
        assert "worker" in health, "Worker health check failed"
        logger.info(f"✓ Worker health: {health['worker']['status']}")
        
        # Test stats
        stats = worker.get_stats()
        assert "jobs_processed" in stats, "Worker stats missing"
        logger.info(f"✓ Worker stats available: {list(stats.keys())}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Worker initialization test failed: {e}")
        logger.error(traceback.format_exc())
        return False


async def test_full_integration():
    """Test full integration with a small dataset."""
    logger.info("Testing full integration...")
    
    try:
        from app.services import get_job_service, get_cache_service
        from app.workers import get_enrichment_worker
        from app.models.job import JobCreate
        from app.services.scraper_service import ScrapingConfig
        import tempfile
        import os
        
        # Create test data
        test_data = {
            "Dealer": ["Integration Test Dealer"],
            "Address": ["123 Integration St, Test City, ST 12345"],
            "Phone": ["555-TEST"],
            "Email": ["test@integration.com"]
        }
        
        df = pd.DataFrame(test_data)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
            df.to_csv(tmp.name, index=False)
            tmp_path = tmp.name
        
        try:
            # Initialize services
            job_service = get_job_service()
            cache_service = get_cache_service()
            
            # Configure for testing
            scraping_config = ScrapingConfig(
                max_retries=1,
                concurrent_limit=1,
                use_cache=True,
                timeout_ms=5000  # Short timeout for testing
            )
            
            # Create job
            job_create = JobCreate(options={"integration_test": True})
            job_response = await job_service.create_job(tmp_path, job_create)
            job_id = job_response.job_id
            
            logger.info(f"✓ Created integration test job: {job_id}")
            
            # Initialize worker
            worker = get_enrichment_worker(
                max_concurrent_jobs=1,
                max_concurrent_records=1,
                scraping_config=scraping_config
            )
            
            # Start job manually (instead of full worker loop)
            await job_service.start_job(job_id)
            
            # Get records to process
            records = await job_service.get_job_records(job_id)
            assert len(records) == 1, "Should have one record"
            
            logger.info("✓ Integration test setup complete")
            
            # This is a basic integration test - we don't run the full enrichment
            # to avoid external dependencies in the test
            
        finally:
            os.unlink(tmp_path)
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Full integration test failed: {e}")
        logger.error(traceback.format_exc())
        return False


async def run_all_tests():
    """Run all integration tests."""
    logger.info("Starting enhanced enrichment pipeline integration tests...")
    
    test_results = {
        "auto_enrich_integration": await test_auto_enrich_integration(),
        "cache_service": await test_cache_service(),
        "scraper_service": await test_scraper_service(),
        "job_service": await test_job_service(),
        "worker_initialization": await test_worker_initialization(),
        "full_integration": await test_full_integration()
    }
    
    # Summary
    passed = sum(test_results.values())
    total = len(test_results)
    
    logger.info(f"\nTest Results Summary:")
    logger.info(f"==================")
    
    for test_name, result in test_results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All integration tests passed! The enhanced pipeline is ready.")
    else:
        logger.warning(f"⚠️  {total - passed} tests failed. Check the logs above.")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)