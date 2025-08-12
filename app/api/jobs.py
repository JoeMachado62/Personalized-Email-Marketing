"""
Job management endpoints.
Handles CRUD operations for enrichment jobs.
"""

import asyncio
import aiofiles
import pandas as pd
import json
from uuid import uuid4
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse
from typing import Optional, Dict, Any

from app.models.job import (
    JobResponse, JobStatusResponse, JobCreate, 
    ProgressInfo, JobStatus
)
from app.db.connection import JobService, get_db
from app.config import settings
from app.services.job_processor import process_job
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/upload", response_model=JobResponse)
async def create_job(
    file: UploadFile = File(...),
    options: Optional[str] = None
):
    """
    Create new enrichment job from uploaded CSV.
    
    Steps:
    1. Validate CSV format
    2. Save file to disk
    3. Create job record in database
    4. Queue for processing
    5. Return job ID and status
    """
    try:
        # Parse options if provided
        job_options = {}
        column_mappings = None
        if options:
            try:
                job_options = json.loads(options)
                column_mappings = job_options.get('column_mappings')
            except json.JSONDecodeError:
                raise HTTPException(400, "Invalid options JSON format")
        
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(400, "Only CSV files are supported")
        
        # Validate file size
        if file.size and file.size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(400, f"File too large. Maximum size: {settings.MAX_FILE_SIZE_MB}MB")
        
        # Generate job ID and file path
        job_id = str(uuid4())
        file_path = settings.UPLOAD_DIR / f"{job_id}.csv"
        
        # Save uploaded file
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        logger.info(f"Saved uploaded file to {file_path}")
        
        # Parse CSV to count records and validate columns
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            # Clean up the file if CSV parsing fails
            file_path.unlink(missing_ok=True)
            raise HTTPException(400, f"Invalid CSV format: {str(e)}")
        
        # If column mappings provided, use them. Otherwise, try auto-detection
        if column_mappings:
            logger.info(f"Using provided column mappings: {column_mappings}")
            # Store mappings for enrichment process
            mapping_file = settings.UPLOAD_DIR / f"{job_id}_mappings.json"
            with open(mapping_file, 'w') as f:
                json.dump(column_mappings, f)
        else:
            # Try flexible auto-detection
            company_col = None
            for col in df.columns:
                col_lower = col.lower()
                # More specific matching - avoid catching unrelated "name" columns
                if any(x in col_lower for x in ['company', 'dealer', 'business']):
                    company_col = col
                    break
                # Check for standalone "name" only if it's the main identifier
                elif col_lower in ['name', 'business name', 'company name', 'dealer name']:
                    company_col = col
                    break
            
            if not company_col:
                # Before failing, provide helpful analysis
                logger.warning(f"Could not auto-detect company column. Available columns: {list(df.columns)}")
                
                # Suggest using column mapper
                file_path.unlink(missing_ok=True)
                raise HTTPException(
                    400, 
                    f"Column auto-detection failed. Please use the Column Mapper at /mapper.html to map your columns. " +
                    f"Found columns: {list(df.columns[:10])}"
                )
            
            # Auto-create basic mappings
            auto_mappings = {}
            for col in df.columns:
                col_lower = col.lower()
                # Check if empty column (enrichment target)
                is_empty = bool(df[col].isna().all() or (df[col].astype(str).str.strip() == '').all())
                
                # Company/Dealer detection - be more specific
                if ('dealer' in col_lower and 'name' in col_lower) or (col_lower == 'dealer name'):
                    auto_mappings[col] = {'field_type': 'company_name', 'is_target': is_empty}
                elif ('company' in col_lower and 'name' in col_lower) or (col_lower == 'company name'):
                    auto_mappings[col] = {'field_type': 'company_name', 'is_target': is_empty}
                elif col_lower == 'business name':
                    auto_mappings[col] = {'field_type': 'company_name', 'is_target': is_empty}
                # Address detection - be specific about location address
                elif ('address' in col_lower) or ('location' in col_lower and 'address' in col_lower):
                    auto_mappings[col] = {'field_type': 'address', 'is_target': is_empty}
                # City detection
                elif 'city' in col_lower:
                    auto_mappings[col] = {'field_type': 'city', 'is_target': is_empty}
                # State detection  
                elif col_lower == 'state' or 'state' in col_lower.split():
                    auto_mappings[col] = {'field_type': 'state', 'is_target': is_empty}
                # ZIP detection
                elif 'zip' in col_lower or 'postal' in col_lower:
                    auto_mappings[col] = {'field_type': 'zip_code', 'is_target': is_empty}
                # Phone detection (non-owner)
                elif 'phone' in col_lower and 'owner' not in col_lower:
                    auto_mappings[col] = {'field_type': 'phone', 'is_target': is_empty}
                # Email detection (non-owner, non-subject)
                elif 'email' in col_lower and 'subject' not in col_lower and 'owner' not in col_lower:
                    auto_mappings[col] = {'field_type': 'email', 'is_target': is_empty}
                # Website/URL detection
                elif 'website' in col_lower or ('dealer' in col_lower and 'url' in col_lower):
                    auto_mappings[col] = {'field_type': 'website', 'is_target': is_empty}
                # Owner-specific fields
                elif 'owner' in col_lower:
                    if 'first' in col_lower and 'name' in col_lower:
                        auto_mappings[col] = {'field_type': 'owner_first_name', 'is_target': is_empty}
                    elif 'last' in col_lower and 'name' in col_lower:
                        auto_mappings[col] = {'field_type': 'owner_last_name', 'is_target': is_empty}
                    elif 'email' in col_lower:
                        auto_mappings[col] = {'field_type': 'owner_email', 'is_target': is_empty}
                    elif 'phone' in col_lower:
                        auto_mappings[col] = {'field_type': 'owner_phone', 'is_target': is_empty}
                # Email subject line detection
                elif 'subject' in col_lower:
                    auto_mappings[col] = {'field_type': 'email_subject', 'is_target': is_empty}
                # Ice breaker detection
                elif ('ice' in col_lower and 'breaker' in col_lower) or ('icebreaker' in col_lower):
                    auto_mappings[col] = {'field_type': 'email_icebreaker', 'is_target': is_empty}
                # Hot button detection
                elif ('hot' in col_lower and 'button' in col_lower) or ('hot button' in col_lower):
                    auto_mappings[col] = {'field_type': 'hot_button', 'is_target': is_empty}
            
            if auto_mappings:
                # Save auto-detected mappings (convert numpy bool to Python bool)
                mapping_file = settings.UPLOAD_DIR / f"{job_id}_mappings.json"
                # Convert numpy bools to Python bools for JSON serialization
                json_safe_mappings = {}
                for col, mapping in auto_mappings.items():
                    json_safe_mappings[col] = {
                        'field_type': mapping['field_type'],
                        'is_target': bool(mapping['is_target'])  # Ensure Python bool
                    }
                with open(mapping_file, 'w') as f:
                    json.dump(json_safe_mappings, f)
                logger.info(f"Auto-detected mappings for {len(auto_mappings)} columns")
            
            logger.info(f"Detected company column: {company_col}")
        
        logger.info(f"CSV has {len(df.columns)} columns: {list(df.columns[:10])}...")
        
        # Check record limit
        if len(df) > settings.MAX_RECORDS_PER_JOB:
            file_path.unlink(missing_ok=True)
            raise HTTPException(400, f"Too many records. Maximum: {settings.MAX_RECORDS_PER_JOB}")
        
        # Create job in database
        JobService.create_job(
            job_id=job_id,
            total_records=len(df),
            input_file_path=str(file_path),
            options=job_options
        )
        
        logger.info(f"Created job {job_id} with {len(df)} records")
        
        # Start processing in background
        # Import moved to module level to avoid import issues
        asyncio.create_task(process_job(job_id))
        logger.info(f"Started background processing for job {job_id}")
        
        return JobResponse(
            job_id=job_id,
            status="pending",
            message="Job created successfully",
            total_records=len(df)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating job: {str(e)}")
        raise HTTPException(500, f"Internal server error: {str(e)}")

@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get job status and progress.
    
    Returns:
    - Job status (pending/processing/completed/failed)
    - Progress percentage
    - Error details if failed
    """
    try:
        job = JobService.get_job(job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        
        # Calculate progress percentage
        progress_percentage = 0.0
        if job['total_records'] > 0:
            progress_percentage = (job['processed_records'] / job['total_records']) * 100
        
        progress = ProgressInfo(
            total_records=job['total_records'],
            processed_records=job['processed_records'],
            failed_records=job['failed_records'],
            percentage=progress_percentage
        )
        
        # Parse timestamps
        created_at = datetime.fromisoformat(job['created_at'].replace('Z', '+00:00'))
        started_at = None
        completed_at = None
        
        if job['started_at']:
            started_at = datetime.fromisoformat(job['started_at'].replace('Z', '+00:00'))
        
        if job['completed_at']:
            completed_at = datetime.fromisoformat(job['completed_at'].replace('Z', '+00:00'))
        
        return JobStatusResponse(
            job_id=job['id'],
            status=job['status'],
            progress=progress,
            created_at=created_at,
            started_at=started_at,
            completed_at=completed_at,
            estimated_completion=None,  # TODO: Calculate based on current progress
            estimated_cost=job['estimated_cost'],
            actual_cost=job['actual_cost'],
            error_message=job.get('error_message')
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status for {job_id}: {str(e)}")
        raise HTTPException(500, f"Internal server error: {str(e)}")

@router.get("/{job_id}/download")
async def download_results(
    job_id: str,
    format: str = Query("csv", regex="^(csv|json)$"),
    include_failed: bool = False
):
    """
    Download enriched results.
    
    Formats:
    - CSV: Traditional spreadsheet format
    - JSON: Structured data with metadata
    """
    try:
        job = JobService.get_job(job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        
        if job['status'] != "completed":
            raise HTTPException(400, f"Job is {job['status']}, not completed")
        
        if format == "csv":
            # Check if enriched CSV already exists
            output_path = settings.OUTPUT_DIR / f"{job_id}_enriched.csv"
            
            # If file exists, serve it directly
            if output_path.exists():
                return FileResponse(
                    output_path,
                    media_type="text/csv",
                    filename=f"enriched_{job_id}.csv"
                )
            
            # Try to get records from database if file doesn't exist
            records = JobService.get_enriched_records(job_id, include_failed)
            
            if not records:
                # No file and no records - enrichment may have saved directly to CSV
                raise HTTPException(404, "Enriched file not found. The enrichment may have failed.")
            
            # Otherwise, generate CSV from database records
            # Flatten records for CSV format
            flattened_records = []
            for record in records:
                flat_record = record['original_data'].copy()
                
                # Add enriched data
                if record.get('enriched_data'):
                    flat_record.update(record['enriched_data'])
                
                # Add generated content
                if record.get('generated_content'):
                    content = record['generated_content']
                    if isinstance(content, dict):
                        # Flatten generated content
                        for key, value in content.items():
                            if isinstance(value, list):
                                # Join list items for CSV
                                flat_record[f"generated_{key}"] = "; ".join(str(v) for v in value)
                            else:
                                flat_record[f"generated_{key}"] = str(value)
                
                # Add metadata
                flat_record['enrichment_status'] = record['status']
                flat_record['processing_time_ms'] = record.get('processing_time_ms')
                flat_record['confidence_score'] = record.get('enrichment_confidence')
                
                flattened_records.append(flat_record)
            
            # Create DataFrame and save
            df = pd.DataFrame(flattened_records)
            df.to_csv(output_path, index=False)
            
            return FileResponse(
                output_path,
                media_type="text/csv",
                filename=f"enriched_{job_id}.csv"
            )
        else:
            # Return JSON - try to read from CSV if records not in DB
            records = JobService.get_enriched_records(job_id, include_failed)
            
            if not records:
                # Try to read from CSV file
                output_path = settings.OUTPUT_DIR / f"{job_id}_enriched.csv"
                if output_path.exists():
                    import pandas as pd
                    df = pd.read_csv(output_path)
                    records = df.to_dict('records')
                else:
                    raise HTTPException(404, "No enriched data found")
            
            return {
                "job_id": job_id,
                "job_status": job['status'],
                "total_records": job['total_records'],
                "processed_records": job['processed_records'],
                "failed_records": job['failed_records'],
                "enriched_records": records,
                "statistics": {
                    "total_processed": job['total_records'],
                    "successful": job['processed_records'] - job['failed_records'],
                    "failed": job['failed_records'],
                    "success_rate": ((job['processed_records'] - job['failed_records']) / job['total_records'] * 100) if job['total_records'] > 0 else 0
                },
                "cost_info": {
                    "estimated_cost": job['estimated_cost'],
                    "actual_cost": job['actual_cost']
                }
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading results for {job_id}: {str(e)}")
        raise HTTPException(500, f"Internal server error: {str(e)}")

@router.get("/")
async def list_jobs(
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """List all jobs with optional filtering"""
    try:
        with get_db() as conn:
            if status:
                cursor = conn.execute("""
                    SELECT * FROM jobs 
                    WHERE status = ?
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, (status, limit, offset))
            else:
                cursor = conn.execute("""
                    SELECT * FROM jobs 
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))
            
            jobs = []
            for row in cursor.fetchall():
                job = dict(row)
                job['options'] = json.loads(job['options'] or '{}')
                jobs.append(job)
            
            return {
                "jobs": jobs,
                "limit": limit,
                "offset": offset,
                "total": len(jobs)
            }
    
    except Exception as e:
        logger.error(f"Error listing jobs: {str(e)}")
        raise HTTPException(500, f"Internal server error: {str(e)}")

@router.delete("/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a pending or processing job"""
    try:
        job = JobService.get_job(job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        
        if job['status'] in ['completed', 'failed', 'cancelled']:
            raise HTTPException(400, f"Cannot cancel job with status: {job['status']}")
        
        JobService.update_status(job_id, 'cancelled')
        
        return {"message": f"Job {job_id} cancelled successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling job {job_id}: {str(e)}")
        raise HTTPException(500, f"Internal server error: {str(e)}")