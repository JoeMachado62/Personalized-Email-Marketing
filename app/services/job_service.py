"""
Job management service for enrichment operations.

This service manages the lifecycle of enrichment jobs, including creation, 
tracking progress, handling failures, and coordinating with the worker system.
It integrates with the database to persist job state and provides APIs for
job monitoring and control.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import sqlite3
import json
import pandas as pd

from ..models.job import Job, JobStatus, Record, RecordStatus, JobCreate, JobResponse, JobStatusResponse, ProgressInfo
from .cache_service import get_cache_service

logger = logging.getLogger(__name__)


class JobService:
    """
    Service for managing enrichment jobs and their lifecycle.
    
    Handles job creation, progress tracking, error recovery, and coordination
    with worker processes. Integrates with the database for persistence and
    provides comprehensive job monitoring capabilities.
    """
    
    def __init__(self, db_path: str = "data/app.db"):
        self.db_path = Path(db_path)
        self.cache_service = get_cache_service()
        self._jobs_in_progress: Dict[str, Job] = {}
        self._job_locks: Dict[str, asyncio.Lock] = {}
        
        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize the job management database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Jobs table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS jobs (
                        id TEXT PRIMARY KEY,
                        status TEXT NOT NULL,
                        total_records INTEGER DEFAULT 0,
                        processed_records INTEGER DEFAULT 0,
                        failed_records INTEGER DEFAULT 0,
                        input_file_path TEXT NOT NULL,
                        output_file_path TEXT,
                        options TEXT DEFAULT '{}',
                        estimated_cost REAL DEFAULT 0.0,
                        actual_cost REAL DEFAULT 0.0,
                        created_at TEXT NOT NULL,
                        started_at TEXT,
                        completed_at TEXT,
                        user_id TEXT DEFAULT 'default',
                        error_message TEXT,
                        processing_time_seconds REAL
                    )
                """)
                
                # Records table for tracking individual record processing
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        job_id TEXT NOT NULL,
                        record_index INTEGER NOT NULL,
                        status TEXT NOT NULL,
                        original_data TEXT NOT NULL,
                        enriched_data TEXT,
                        generated_content TEXT,
                        processing_attempts INTEGER DEFAULT 0,
                        last_error TEXT,
                        processing_time_ms INTEGER,
                        llm_tokens_used INTEGER,
                        cost REAL DEFAULT 0.0,
                        enrichment_confidence REAL,
                        data_completeness REAL,
                        created_at TEXT NOT NULL,
                        processed_at TEXT,
                        FOREIGN KEY (job_id) REFERENCES jobs (id)
                    )
                """)
                
                # Create indexes for performance
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_records_job_id ON records(job_id)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_records_status ON records(status)
                """)
                
                conn.commit()
                logger.info("Job management database initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize job database: {e}")
            raise
    
    async def create_job(self, input_file_path: str, job_create: JobCreate) -> JobResponse:
        """
        Create a new enrichment job.
        
        Args:
            input_file_path: Path to the input CSV file
            job_create: Job creation parameters
            
        Returns:
            JobResponse with job details
        """
        try:
            # Validate input file exists
            if not Path(input_file_path).exists():
                raise ValueError(f"Input file not found: {input_file_path}")
            
            # Read CSV to get record count and validate format
            try:
                df = pd.read_csv(input_file_path)
                total_records = len(df)
                
                # Validate required columns exist
                required_columns = self._get_required_columns(df.columns.tolist())
                if not required_columns:
                    raise ValueError("Input file does not contain required dealer information columns")
                    
            except Exception as e:
                raise ValueError(f"Failed to read input CSV file: {e}")
            
            # Generate unique job ID
            job_id = str(uuid.uuid4())
            
            # Calculate estimated cost
            estimated_cost = self._estimate_job_cost(total_records, job_create.options)
            
            # Create output file path
            input_path = Path(input_file_path)
            output_file_path = str(input_path.parent / f"{input_path.stem}_enriched_{job_id[:8]}.csv")
            
            # Create job object
            job = Job(
                id=job_id,
                status=JobStatus.PENDING,
                total_records=total_records,
                input_file_path=input_file_path,
                output_file_path=output_file_path,
                options=job_create.options,
                estimated_cost=estimated_cost,
                created_at=datetime.now()
            )
            
            # Save job to database
            await self._save_job_to_db(job)
            
            # Create individual record entries
            await self._create_record_entries(job, df)
            
            logger.info(f"Created job {job_id} with {total_records} records, estimated cost: ${estimated_cost:.2f}")
            
            return JobResponse(
                job_id=job_id,
                status=job.status.value,
                message="Job created successfully",
                total_records=total_records
            )
            
        except Exception as e:
            logger.error(f"Failed to create job: {e}")
            raise
    
    def _get_required_columns(self, columns: List[str]) -> Dict[str, str]:
        """Identify required columns from the CSV."""
        column_map = {}
        columns_lower = [col.lower() for col in columns]
        
        # Find dealer name column
        for col in columns:
            if any(keyword in col.lower() for keyword in ['dealer', 'company', 'business', 'name']):
                if 'name' in col.lower():
                    column_map['name'] = col
                    break
        
        # Find address column
        for col in columns:
            if 'address' in col.lower():
                column_map['address'] = col
                break
        
        # Find phone column
        for col in columns:
            if 'phone' in col.lower():
                column_map['phone'] = col
                break
        
        # Find email column (optional)
        for col in columns:
            if 'email' in col.lower():
                column_map['email'] = col
                break
        
        # Return only if we have at least name and address
        if 'name' in column_map and ('address' in column_map or 'phone' in column_map):
            return column_map
        
        return {}
    
    def _estimate_job_cost(self, record_count: int, options: Dict[str, Any]) -> float:
        """Estimate the cost of processing a job."""
        # Base cost per record for website search and AI content generation
        base_cost_per_record = 0.15  # $0.15 per record
        
        # Adjust based on options
        multiplier = 1.0
        if options.get('include_contact_extraction', False):
            multiplier += 0.5  # Additional cost for contact extraction
        
        if options.get('premium_ai_model', False):
            multiplier += 1.0  # Premium models cost more
        
        # Calculate with some headroom
        estimated_cost = record_count * base_cost_per_record * multiplier * 1.2
        
        return round(estimated_cost, 2)
    
    async def _save_job_to_db(self, job: Job) -> None:
        """Save job to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO jobs (
                        id, status, total_records, processed_records, failed_records,
                        input_file_path, output_file_path, options, estimated_cost,
                        actual_cost, created_at, started_at, completed_at, user_id,
                        error_message, processing_time_seconds
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job.id, job.status.value, job.total_records, job.processed_records,
                    job.failed_records, job.input_file_path, job.output_file_path,
                    json.dumps(job.options), job.estimated_cost, job.actual_cost,
                    job.created_at.isoformat(),
                    job.started_at.isoformat() if job.started_at else None,
                    job.completed_at.isoformat() if job.completed_at else None,
                    job.user_id, job.error_message, job.processing_time_seconds
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to save job to database: {e}")
            raise
    
    async def _create_record_entries(self, job: Job, df: pd.DataFrame) -> None:
        """Create individual record entries for the job."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                for idx, row in df.iterrows():
                    record = Record(
                        id=0,  # Auto-increment
                        job_id=job.id,
                        record_index=idx,
                        status=RecordStatus.PENDING,
                        original_data=row.to_dict(),
                        created_at=datetime.now()
                    )
                    
                    conn.execute("""
                        INSERT INTO records (
                            job_id, record_index, status, original_data, enriched_data,
                            generated_content, processing_attempts, last_error,
                            processing_time_ms, llm_tokens_used, cost,
                            enrichment_confidence, data_completeness, created_at, processed_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        record.job_id, record.record_index, record.status.value,
                        json.dumps(record.original_data),
                        json.dumps(record.enriched_data) if record.enriched_data else None,
                        json.dumps(record.generated_content) if record.generated_content else None,
                        record.processing_attempts, record.last_error,
                        record.processing_time_ms, record.llm_tokens_used, record.cost,
                        record.enrichment_confidence, record.data_completeness,
                        record.created_at.isoformat(),
                        record.processed_at.isoformat() if record.processed_at else None
                    ))
                
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to create record entries: {e}")
            raise
    
    async def get_job_status(self, job_id: str) -> Optional[JobStatusResponse]:
        """
        Get current status of a job.
        
        Args:
            job_id: The job identifier
            
        Returns:
            JobStatusResponse with current status or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT * FROM jobs WHERE id = ?
                """, (job_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                # Convert row to Job object
                job = self._row_to_job(row)
                
                # Calculate progress
                progress = ProgressInfo(
                    total_records=job.total_records,
                    processed_records=job.processed_records,
                    failed_records=job.failed_records,
                    percentage=round((job.processed_records + job.failed_records) / job.total_records * 100, 2) if job.total_records > 0 else 0
                )
                
                # Estimate completion time
                estimated_completion = None
                if job.status == JobStatus.PROCESSING and job.started_at:
                    remaining_records = job.total_records - job.processed_records - job.failed_records
                    if remaining_records > 0 and job.processed_records > 0:
                        elapsed = datetime.now() - job.started_at
                        rate = job.processed_records / elapsed.total_seconds()  # records per second
                        remaining_seconds = remaining_records / rate if rate > 0 else 0
                        estimated_completion = datetime.now() + timedelta(seconds=remaining_seconds)
                
                return JobStatusResponse(
                    job_id=job.id,
                    status=job.status.value,
                    progress=progress,
                    created_at=job.created_at,
                    started_at=job.started_at,
                    completed_at=job.completed_at,
                    estimated_completion=estimated_completion,
                    estimated_cost=job.estimated_cost,
                    actual_cost=job.actual_cost,
                    error_message=job.error_message
                )
                
        except Exception as e:
            logger.error(f"Failed to get job status: {e}")
            return None
    
    def _row_to_job(self, row: sqlite3.Row) -> Job:
        """Convert database row to Job object."""
        return Job(
            id=row[0],
            status=JobStatus(row[1]),
            total_records=row[2],
            processed_records=row[3],
            failed_records=row[4],
            input_file_path=row[5],
            output_file_path=row[6],
            options=json.loads(row[7]) if row[7] else {},
            estimated_cost=row[8],
            actual_cost=row[9],
            created_at=datetime.fromisoformat(row[10]),
            started_at=datetime.fromisoformat(row[11]) if row[11] else None,
            completed_at=datetime.fromisoformat(row[12]) if row[12] else None,
            user_id=row[13],
            error_message=row[14],
            processing_time_seconds=row[15]
        )
    
    async def start_job(self, job_id: str) -> bool:
        """
        Mark a job as started and ready for processing.
        
        Args:
            job_id: The job identifier
            
        Returns:
            True if job was started successfully, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    UPDATE jobs 
                    SET status = ?, started_at = ?
                    WHERE id = ? AND status = ?
                """, (JobStatus.PROCESSING.value, datetime.now().isoformat(), 
                      job_id, JobStatus.PENDING.value))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    logger.info(f"Job {job_id} started successfully")
                    return True
                else:
                    logger.warning(f"Failed to start job {job_id} - may not be in pending status")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to start job {job_id}: {e}")
            return False
    
    async def complete_job(self, job_id: str, success: bool = True, 
                          error_message: Optional[str] = None) -> bool:
        """
        Mark a job as completed.
        
        Args:
            job_id: The job identifier
            success: Whether the job completed successfully
            error_message: Error message if job failed
            
        Returns:
            True if job was marked as completed successfully
        """
        try:
            status = JobStatus.COMPLETED if success else JobStatus.FAILED
            completed_at = datetime.now()
            
            # Calculate actual processing time
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT started_at FROM jobs WHERE id = ?
                """, (job_id,))
                
                row = cursor.fetchone()
                processing_time = None
                if row and row[0]:
                    started_at = datetime.fromisoformat(row[0])
                    processing_time = (completed_at - started_at).total_seconds()
                
                # Update job status
                cursor = conn.execute("""
                    UPDATE jobs 
                    SET status = ?, completed_at = ?, error_message = ?, 
                        processing_time_seconds = ?
                    WHERE id = ?
                """, (status.value, completed_at.isoformat(), 
                      error_message, processing_time, job_id))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    logger.info(f"Job {job_id} marked as {status.value}")
                    return True
                else:
                    logger.warning(f"Failed to complete job {job_id} - job not found")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to complete job {job_id}: {e}")
            return False
    
    async def update_record_progress(self, job_id: str, record_index: int,
                                   status: RecordStatus, enriched_data: Optional[Dict[str, Any]] = None,
                                   error_message: Optional[str] = None,
                                   processing_time_ms: Optional[int] = None,
                                   cost: float = 0.0) -> None:
        """
        Update the status of a specific record within a job.
        
        Args:
            job_id: The job identifier
            record_index: Index of the record within the job
            status: New status of the record
            enriched_data: Enriched data if successful
            error_message: Error message if failed
            processing_time_ms: Processing time in milliseconds
            cost: Cost incurred for processing this record
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Update record status
                conn.execute("""
                    UPDATE records 
                    SET status = ?, enriched_data = ?, last_error = ?, 
                        processing_time_ms = ?, cost = ?, processed_at = ?,
                        processing_attempts = processing_attempts + 1
                    WHERE job_id = ? AND record_index = ?
                """, (
                    status.value,
                    json.dumps(enriched_data) if enriched_data else None,
                    error_message,
                    processing_time_ms,
                    cost,
                    datetime.now().isoformat(),
                    job_id,
                    record_index
                ))
                
                # Update job-level counters
                if status == RecordStatus.ENRICHED:
                    conn.execute("""
                        UPDATE jobs 
                        SET processed_records = processed_records + 1,
                            actual_cost = actual_cost + ?
                        WHERE id = ?
                    """, (cost, job_id))
                elif status == RecordStatus.FAILED:
                    conn.execute("""
                        UPDATE jobs 
                        SET failed_records = failed_records + 1,
                            actual_cost = actual_cost + ?
                        WHERE id = ?
                    """, (cost, job_id))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to update record progress: {e}")
    
    async def get_pending_jobs(self, limit: int = 10) -> List[Job]:
        """
        Get list of jobs waiting to be processed.
        
        Args:
            limit: Maximum number of jobs to return
            
        Returns:
            List of pending Job objects
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT * FROM jobs 
                    WHERE status = ? 
                    ORDER BY created_at ASC 
                    LIMIT ?
                """, (JobStatus.PENDING.value, limit))
                
                jobs = []
                for row in cursor.fetchall():
                    jobs.append(self._row_to_job(row))
                
                return jobs
                
        except Exception as e:
            logger.error(f"Failed to get pending jobs: {e}")
            return []
    
    async def get_job_records(self, job_id: str, status_filter: Optional[RecordStatus] = None) -> List[Record]:
        """
        Get records for a specific job.
        
        Args:
            job_id: The job identifier
            status_filter: Optional status to filter records
            
        Returns:
            List of Record objects
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                if status_filter:
                    cursor = conn.execute("""
                        SELECT * FROM records 
                        WHERE job_id = ? AND status = ?
                        ORDER BY record_index ASC
                    """, (job_id, status_filter.value))
                else:
                    cursor = conn.execute("""
                        SELECT * FROM records 
                        WHERE job_id = ?
                        ORDER BY record_index ASC
                    """, (job_id,))
                
                records = []
                for row in cursor.fetchall():
                    records.append(self._row_to_record(row))
                
                return records
                
        except Exception as e:
            logger.error(f"Failed to get job records: {e}")
            return []
    
    def _row_to_record(self, row: sqlite3.Row) -> Record:
        """Convert database row to Record object."""
        return Record(
            id=row[0],
            job_id=row[1],
            record_index=row[2],
            status=RecordStatus(row[3]),
            original_data=json.loads(row[4]),
            enriched_data=json.loads(row[5]) if row[5] else None,
            generated_content=json.loads(row[6]) if row[6] else None,
            processing_attempts=row[7],
            last_error=row[8],
            processing_time_ms=row[9],
            llm_tokens_used=row[10],
            cost=row[11],
            enrichment_confidence=row[12],
            data_completeness=row[13],
            created_at=datetime.fromisoformat(row[14]),
            processed_at=datetime.fromisoformat(row[15]) if row[15] else None
        )
    
    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job that is pending or in progress.
        
        Args:
            job_id: The job identifier
            
        Returns:
            True if job was cancelled successfully
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    UPDATE jobs 
                    SET status = ?, completed_at = ?
                    WHERE id = ? AND status IN (?, ?)
                """, (JobStatus.CANCELLED.value, datetime.now().isoformat(),
                      job_id, JobStatus.PENDING.value, JobStatus.PROCESSING.value))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    logger.info(f"Job {job_id} cancelled successfully")
                    return True
                else:
                    logger.warning(f"Failed to cancel job {job_id} - may not be cancellable")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            return False
    
    async def cleanup_old_jobs(self, days_old: int = 30) -> int:
        """
        Clean up old completed/failed jobs.
        
        Args:
            days_old: Remove jobs older than this many days
            
        Returns:
            Number of jobs removed
        """
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # First delete associated records
                cursor = conn.execute("""
                    DELETE FROM records 
                    WHERE job_id IN (
                        SELECT id FROM jobs 
                        WHERE completed_at < ? AND status IN (?, ?, ?)
                    )
                """, (cutoff_date.isoformat(), JobStatus.COMPLETED.value,
                      JobStatus.FAILED.value, JobStatus.CANCELLED.value))
                
                records_removed = cursor.rowcount
                
                # Then delete jobs
                cursor = conn.execute("""
                    DELETE FROM jobs 
                    WHERE completed_at < ? AND status IN (?, ?, ?)
                """, (cutoff_date.isoformat(), JobStatus.COMPLETED.value,
                      JobStatus.FAILED.value, JobStatus.CANCELLED.value))
                
                jobs_removed = cursor.rowcount
                conn.commit()
                
                if jobs_removed > 0:
                    logger.info(f"Cleaned up {jobs_removed} old jobs and {records_removed} associated records")
                
                return jobs_removed
                
        except Exception as e:
            logger.error(f"Failed to cleanup old jobs: {e}")
            return 0


# Global service instance
_job_service: Optional[JobService] = None


def get_job_service(db_path: str = "data/app.db") -> JobService:
    """Get the global job service instance."""
    global _job_service
    if _job_service is None:
        _job_service = JobService(db_path)
    return _job_service