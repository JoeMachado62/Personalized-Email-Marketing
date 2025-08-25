"""
Background job processor for enrichment tasks.
"""

import asyncio
import logging
from pathlib import Path
from datetime import datetime
import pandas as pd
import json

from app.db.connection import JobService, get_db
from app.config import settings
from auto_enrich.enricher import enrich_dataframe

logger = logging.getLogger(__name__)


async def process_job(job_id: str):
    """
    Process an enrichment job asynchronously.
    
    Args:
        job_id: The job ID to process
    """
    logger.info(f"Starting processing for job {job_id}")
    
    try:
        # Update job status to processing
        JobService.update_status(job_id, 'processing')
        JobService.update_job(job_id, {'started_at': datetime.utcnow().isoformat()})
        
        # Get job details
        job = JobService.get_job(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return
        
        # Load the input CSV
        input_path = Path(job['input_file_path'])
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        logger.info(f"Loading CSV from {input_path}")
        df = pd.read_csv(input_path)
        
        # Check for column mappings
        mapping_file = settings.UPLOAD_DIR / f"{job_id}_mappings.json"
        
        # Extract processing configuration from job options
        processing_config = None
        campaign_context = None
        if job.get('options'):
            try:
                options = json.loads(job['options']) if isinstance(job['options'], str) else job['options']
                campaign_context = options.get('campaign_context', {})
                processing_config = campaign_context.get('processing_config')
                
                if processing_config:
                    enabled_steps = processing_config.get('enabled_steps', [])
                    logger.info(f"Using processing configuration with {len(enabled_steps)} enabled steps: {enabled_steps}")
                else:
                    logger.info("No processing configuration found, using default enrichment pipeline")
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.warning(f"Failed to parse processing configuration: {e}")
                processing_config = None
        
        logger.info(f"Starting enrichment for {len(df)} records")
        
        # Process in batches to avoid overwhelming the API
        batch_size = 100  # Process 100 records at a time
        total_records = len(df)
        processed_records = 0
        
        # Create output dataframe
        enriched_df = pd.DataFrame()
        
        for start_idx in range(0, total_records, batch_size):
            end_idx = min(start_idx + batch_size, total_records)
            batch_df = df.iloc[start_idx:end_idx]
            
            logger.info(f"Processing batch {start_idx}-{end_idx} of {total_records}")
            
            try:
                # Enrich the batch
                enriched_batch = await enrich_dataframe(
                    batch_df, 
                    concurrent_tasks=settings.MAX_CONCURRENT_ENRICHMENTS,
                    mapping_file=mapping_file if mapping_file.exists() else None,
                    processing_config=processing_config
                )
                
                # Append to results
                enriched_df = pd.concat([enriched_df, enriched_batch], ignore_index=True)
                
                # Update progress
                processed_records = end_idx
                JobService.update_job(job_id, {
                    'processed_records': processed_records
                    # progress_percentage removed - calculated on the fly in API
                })
                
                logger.info(f"Processed {processed_records}/{total_records} records")
                
            except Exception as e:
                logger.error(f"Error processing batch {start_idx}-{end_idx}: {str(e)}")
                # Continue with next batch even if one fails
                JobService.update_job(job_id, {
                    'failed_records': JobService.get_job(job_id)['failed_records'] + (end_idx - start_idx)
                })
        
        # Save enriched data
        output_path = settings.OUTPUT_DIR / f"{job_id}_enriched.csv"
        enriched_df.to_csv(output_path, index=False)
        logger.info(f"Saved enriched data to {output_path}")
        
        # Update job as completed
        JobService.update_status(job_id, 'completed')
        JobService.update_job(job_id, {
            'completed_at': datetime.utcnow().isoformat(),
            'output_file_path': str(output_path),
            'processed_records': processed_records
        })
        
        logger.info(f"Job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {str(e)}")
        JobService.update_status(job_id, 'failed')
        JobService.update_job(job_id, {
            'completed_at': datetime.utcnow().isoformat(),
            'error_message': str(e)
        })


# Background task runner
async def start_job_processor():
    """
    Start the background job processor.
    Checks for pending jobs and processes them.
    """
    logger.info("Starting job processor service")
    
    while True:
        try:
            # Check for pending jobs
            with get_db() as conn:
                cursor = conn.execute(
                    "SELECT id FROM jobs WHERE status = 'pending' ORDER BY created_at LIMIT 1"
                )
                row = cursor.fetchone()
                
                if row:
                    job_id = row[0] if isinstance(row, tuple) else row['id']
                    logger.info(f"Found pending job: {job_id}")
                    await process_job(job_id)
                else:
                    # No pending jobs, wait a bit
                    await asyncio.sleep(5)
                    
        except Exception as e:
            logger.error(f"Error in job processor: {str(e)}")
            await asyncio.sleep(10)