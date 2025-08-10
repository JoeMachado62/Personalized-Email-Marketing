"""
Async worker for processing enrichment jobs.

This worker processes enrichment jobs by coordinating between the job service,
scraper service, cache service, and the existing auto_enrich modules. It handles
bulk processing with proper concurrency control, error recovery, and cost tracking.
"""

import asyncio
import logging
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import pandas as pd

from auto_enrich.enricher import DealerRecord
from auto_enrich.ai_enrichment import generate_email_content
from ..models.job import Job, JobStatus, Record, RecordStatus
from ..services.job_service import get_job_service, JobService
from ..services.scraper_service import get_scraper_service, EnhancedScraperService, ScrapingConfig
from ..services.cache_service import get_cache_service, CacheService

logger = logging.getLogger(__name__)


class EnrichmentWorker:
    """
    Async worker that processes enrichment jobs with enhanced capabilities.
    
    This worker integrates all services to provide:
    - Bulk processing with concurrency control
    - Enhanced error handling and retries
    - Cost tracking and optimization
    - Progress monitoring and reporting
    - Integration with existing auto_enrich modules
    """
    
    def __init__(self, 
                 max_concurrent_jobs: int = 1,
                 max_concurrent_records: int = 3,
                 scraping_config: Optional[ScrapingConfig] = None):
        """
        Initialize the enrichment worker.
        
        Args:
            max_concurrent_jobs: Maximum number of jobs to process simultaneously
            max_concurrent_records: Maximum number of records to process per job
            scraping_config: Configuration for scraping operations
        """
        self.max_concurrent_jobs = max_concurrent_jobs
        self.max_concurrent_records = max_concurrent_records
        
        # Initialize services
        self.job_service = get_job_service()
        self.scraper_service = get_scraper_service(scraping_config)
        self.cache_service = get_cache_service()
        
        # Worker state
        self._running = False
        self._current_jobs: Dict[str, asyncio.Task] = {}
        self._job_semaphore = asyncio.Semaphore(max_concurrent_jobs)
        
        # Statistics
        self.stats = {
            "jobs_processed": 0,
            "records_processed": 0,
            "records_failed": 0,
            "total_cost": 0.0,
            "total_processing_time": 0.0,
            "cache_hits": 0,
            "started_at": None
        }
    
    async def start(self) -> None:
        """Start the worker to process jobs."""
        if self._running:
            logger.warning("Worker is already running")
            return
        
        self._running = True
        self.stats["started_at"] = datetime.now()
        logger.info("Enrichment worker started")
        
        try:
            while self._running:
                await self._process_pending_jobs()
                await asyncio.sleep(5)  # Check for new jobs every 5 seconds
                
        except asyncio.CancelledError:
            logger.info("Worker cancelled, shutting down gracefully")
        except Exception as e:
            logger.error(f"Unexpected error in worker: {e}")
            logger.error(traceback.format_exc())
        finally:
            await self._shutdown()
    
    async def stop(self) -> None:
        """Stop the worker gracefully."""
        self._running = False
        logger.info("Stopping enrichment worker...")
    
    async def _shutdown(self) -> None:
        """Gracefully shutdown the worker."""
        # Wait for current jobs to complete
        if self._current_jobs:
            logger.info(f"Waiting for {len(self._current_jobs)} jobs to complete...")
            await asyncio.gather(*self._current_jobs.values(), return_exceptions=True)
        
        logger.info("Enrichment worker stopped")
    
    async def _process_pending_jobs(self) -> None:
        """Process pending jobs from the queue."""
        try:
            # Clean up completed job tasks
            completed_jobs = [job_id for job_id, task in self._current_jobs.items() if task.done()]
            for job_id in completed_jobs:
                del self._current_jobs[job_id]
            
            # Check if we can process more jobs
            if len(self._current_jobs) >= self.max_concurrent_jobs:
                return
            
            # Get pending jobs
            available_slots = self.max_concurrent_jobs - len(self._current_jobs)
            pending_jobs = await self.job_service.get_pending_jobs(limit=available_slots)
            
            for job in pending_jobs:
                if not self._running:
                    break
                
                # Start processing the job
                task = asyncio.create_task(self._process_job(job))
                self._current_jobs[job.id] = task
                logger.info(f"Started processing job {job.id}")
                
        except Exception as e:
            logger.error(f"Error processing pending jobs: {e}")
    
    async def _process_job(self, job: Job) -> None:
        """
        Process a single enrichment job.
        
        Args:
            job: The job to process
        """
        job_start_time = datetime.now()
        
        try:
            # Mark job as started
            await self.job_service.start_job(job.id)
            logger.info(f"Processing job {job.id} with {job.total_records} records")
            
            # Read input CSV
            df = pd.read_csv(job.input_file_path)
            
            # Get pending records for this job
            pending_records = await self.job_service.get_job_records(job.id, RecordStatus.PENDING)
            
            if not pending_records:
                logger.warning(f"No pending records found for job {job.id}")
                await self.job_service.complete_job(job.id, success=True)
                return
            
            # Process records in batches with concurrency control
            semaphore = asyncio.Semaphore(self.max_concurrent_records)
            tasks = []
            
            for record in pending_records:
                if not self._running:
                    break
                
                task = asyncio.create_task(
                    self._process_record_with_semaphore(job.id, record, semaphore)
                )
                tasks.append(task)
            
            # Wait for all records to be processed
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count results
            successful = sum(1 for r in results if r is True)
            failed = sum(1 for r in results if r is not True)
            
            # Generate output file if there were successful records
            if successful > 0:
                await self._generate_output_file(job)
            
            # Mark job as completed
            processing_time = (datetime.now() - job_start_time).total_seconds()
            await self.job_service.complete_job(job.id, success=True)
            
            # Update statistics
            self.stats["jobs_processed"] += 1
            self.stats["records_processed"] += successful
            self.stats["records_failed"] += failed
            self.stats["total_processing_time"] += processing_time
            
            logger.info(f"Job {job.id} completed: {successful} successful, {failed} failed, "
                       f"{processing_time:.2f}s")
            
        except Exception as e:
            error_msg = f"Job processing failed: {str(e)}"
            logger.error(f"Error processing job {job.id}: {error_msg}")
            logger.error(traceback.format_exc())
            
            await self.job_service.complete_job(job.id, success=False, error_message=error_msg)
    
    async def _process_record_with_semaphore(self, job_id: str, record: Record, 
                                           semaphore: asyncio.Semaphore) -> bool:
        """Process a single record with concurrency control."""
        async with semaphore:
            return await self._process_record(job_id, record)
    
    async def _process_record(self, job_id: str, record: Record) -> bool:
        """
        Process a single record for enrichment.
        
        Args:
            job_id: ID of the job this record belongs to
            record: The record to process
            
        Returns:
            True if processing was successful, False otherwise
        """
        start_time = datetime.now()
        cost = 0.0
        
        try:
            # Extract record data
            original_data = record.original_data
            dealer_name = str(original_data.get('Dealer', original_data.get('Name', ''))).strip()
            address = str(original_data.get('Address', '')).strip()
            phone = str(original_data.get('Phone', '')).strip()
            email = original_data.get('Email', None)
            
            if not dealer_name:
                raise ValueError("No dealer name found in record")
            
            # Create DealerRecord object
            dealer_record = DealerRecord(
                idx=record.record_index,
                name=dealer_name,
                address=address,
                phone=phone,
                email=email
            )
            
            # Enrich the record
            enriched_data = await self._enrich_dealer_record(dealer_record)
            cost = enriched_data.get('_processing_cost', 0.0)
            
            # Update record as successful
            processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            await self.job_service.update_record_progress(
                job_id=job_id,
                record_index=record.record_index,
                status=RecordStatus.ENRICHED,
                enriched_data=enriched_data,
                processing_time_ms=processing_time_ms,
                cost=cost
            )
            
            self.stats["total_cost"] += cost
            
            logger.debug(f"Record {record.record_index} processed successfully for {dealer_name}")
            return True
            
        except Exception as e:
            error_msg = f"Record processing failed: {str(e)}"
            logger.error(f"Error processing record {record.record_index}: {error_msg}")
            
            processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            await self.job_service.update_record_progress(
                job_id=job_id,
                record_index=record.record_index,
                status=RecordStatus.FAILED,
                error_message=error_msg,
                processing_time_ms=processing_time_ms,
                cost=cost
            )
            
            return False
    
    async def _enrich_dealer_record(self, record: DealerRecord) -> Dict[str, Any]:
        """
        Enrich a single dealer record with website discovery and AI content.
        
        Args:
            record: DealerRecord to enrich
            
        Returns:
            Dictionary with enriched data
        """
        cost = 0.0
        cached_results = 0
        
        try:
            # Step 1: Website discovery with caching
            website = None
            if not record.website and record.city:
                # Check cache first
                cached_website = await self.cache_service.get_website_cache(record.name, record.city)
                if cached_website is not None:
                    website = cached_website
                    cached_results += 1
                else:
                    # Use enhanced scraper service
                    scrape_result = await self.scraper_service.find_dealer_website_enhanced(
                        record.name, record.city
                    )
                    if scrape_result.success:
                        website = scrape_result.website
                        cost += scrape_result.cost_estimate
                        
                        # Cache the result
                        if not scrape_result.cached:
                            await self.cache_service.set_website_cache(
                                record.name, record.city, website, cost_saved=0.10
                            )
            
            record.website = website
            
            # Step 2: AI content generation with caching
            subject, icebreaker, hot_button = "", "", ""
            
            # Check cache for AI content
            cached_content = await self.cache_service.get_ai_content_cache(
                record.name, record.city, record.website, record.email
            )
            
            if cached_content:
                subject, icebreaker, hot_button = cached_content
                cached_results += 1
            else:
                # Generate AI content using existing module
                subject, icebreaker, hot_button = await generate_email_content(
                    dealer_name=record.name,
                    city=record.city,
                    current_website=record.website,
                    owner_email=record.email,
                    extra_context=None
                )
                
                # Estimate cost for AI content generation
                ai_cost = 0.05  # Estimated cost per AI generation
                cost += ai_cost
                
                # Cache the AI content
                await self.cache_service.set_ai_content_cache(
                    record.name, record.city, record.website, record.email,
                    (subject, icebreaker, hot_button), cost_saved=ai_cost
                )
            
            # Update record with AI content
            record.update_from_ai(subject, icebreaker, hot_button)
            
            # Step 3: Enhanced contact information (if needed)
            if website and not (record.owner_phone or record.owner_email):
                contact_result = await self.scraper_service.extract_contact_info_enhanced(website)
                if contact_result.success and contact_result.contact_info:
                    record.update_from_scraper(website, contact_result.contact_info)
                    cost += contact_result.cost_estimate
            
            # Prepare enriched data
            enriched_data = record.to_dict()
            enriched_data['_processing_cost'] = cost
            enriched_data['_cached_results'] = cached_results
            enriched_data['_website_discovered'] = bool(website)
            enriched_data['_ai_content_generated'] = bool(subject and icebreaker and hot_button)
            
            if cached_results > 0:
                self.stats["cache_hits"] += cached_results
            
            return enriched_data
            
        except Exception as e:
            logger.error(f"Error enriching dealer record for {record.name}: {e}")
            raise
    
    async def _generate_output_file(self, job: Job) -> None:
        """
        Generate the final output CSV file for a completed job.
        
        Args:
            job: The completed job
        """
        try:
            # Read original input file
            df = pd.read_csv(job.input_file_path)
            
            # Get all processed records
            records = await self.job_service.get_job_records(job.id)
            
            # Create enrichment data
            enrichment_rows = []
            
            for record in records:
                enrichment_row = {}
                
                if record.status == RecordStatus.ENRICHED and record.enriched_data:
                    # Use enriched data
                    enrichment_row = record.enriched_data.copy()
                    # Remove internal fields
                    enrichment_row.pop('_processing_cost', None)
                    enrichment_row.pop('_cached_results', None)
                    enrichment_row.pop('_website_discovered', None)
                    enrichment_row.pop('_ai_content_generated', None)
                else:
                    # Fill with empty values for failed records
                    enrichment_row = {
                        'Website': None,
                        'Owner First Name': None,
                        'Owner Last Name': None,
                        'Owner Phone Number': None,
                        'Owner Email': None,
                        'Personalized Email Subject Line': None,
                        'Multi Line Personalized Email Start Ice Breaker': None,
                        'Dealer Hot Button Topic': None,
                    }
                
                enrichment_rows.append(enrichment_row)
            
            # Create enrichment DataFrame
            enrichment_df = pd.DataFrame(enrichment_rows, index=df.index)
            
            # Combine original data with enriched data
            result_df = pd.concat([df.reset_index(drop=True), enrichment_df], axis=1)
            
            # Write output file
            output_path = Path(job.output_file_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            result_df.to_csv(output_path, index=False)
            
            logger.info(f"Generated output file: {output_path}")
            
        except Exception as e:
            logger.error(f"Error generating output file for job {job.id}: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get worker statistics."""
        uptime = None
        if self.stats["started_at"]:
            uptime = (datetime.now() - self.stats["started_at"]).total_seconds()
        
        return {
            **self.stats,
            "uptime_seconds": uptime,
            "currently_processing": len(self._current_jobs),
            "running": self._running,
            "cache_stats": self.cache_service.get_stats()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check of the worker and its services."""
        health = {
            "worker": {
                "status": "healthy" if self._running else "stopped",
                "active_jobs": len(self._current_jobs),
                "stats": self.get_stats()
            }
        }
        
        # Check scraper service
        try:
            scraper_health = await self.scraper_service.health_check()
            health["scraper_service"] = scraper_health
        except Exception as e:
            health["scraper_service"] = {"status": "unhealthy", "error": str(e)}
        
        # Check cache service
        try:
            health["cache_service"] = {
                "status": "healthy",
                "stats": self.cache_service.get_stats()
            }
        except Exception as e:
            health["cache_service"] = {"status": "unhealthy", "error": str(e)}
        
        return health


# Global worker instance
_worker_instance: Optional[EnrichmentWorker] = None


def get_enrichment_worker(max_concurrent_jobs: int = 1,
                         max_concurrent_records: int = 3,
                         scraping_config: Optional[ScrapingConfig] = None) -> EnrichmentWorker:
    """Get the global enrichment worker instance."""
    global _worker_instance
    if _worker_instance is None:
        _worker_instance = EnrichmentWorker(
            max_concurrent_jobs=max_concurrent_jobs,
            max_concurrent_records=max_concurrent_records,
            scraping_config=scraping_config
        )
    return _worker_instance


async def start_worker_process() -> None:
    """Start the worker process with default configuration."""
    # Configure scraping for production use
    scraping_config = ScrapingConfig(
        max_retries=3,
        concurrent_limit=3,
        use_cache=True,
        cache_ttl_hours=24,
        timeout_ms=30000
    )
    
    worker = get_enrichment_worker(
        max_concurrent_jobs=1,
        max_concurrent_records=3,
        scraping_config=scraping_config
    )
    
    logger.info("Starting enrichment worker process...")
    await worker.start()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    # Start the worker
    try:
        asyncio.run(start_worker_process())
    except KeyboardInterrupt:
        logger.info("Worker process interrupted by user")
    except Exception as e:
        logger.error(f"Worker process failed: {e}")
        logger.error(traceback.format_exc())