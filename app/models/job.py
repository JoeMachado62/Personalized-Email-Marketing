"""
Pydantic models for job management.
Defines data structures for enrichment jobs and their responses.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class JobCreate(BaseModel):
    """Model for creating a new job"""
    options: Optional[Dict[str, Any]] = Field(default_factory=dict)

class JobResponse(BaseModel):
    """Response model for job creation"""
    job_id: str
    status: str
    message: str
    total_records: int

class ProgressInfo(BaseModel):
    """Job progress information"""
    total_records: int
    processed_records: int
    failed_records: int
    percentage: float

class JobStatusResponse(BaseModel):
    """Detailed job status response"""
    job_id: str
    status: str
    progress: ProgressInfo
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    estimated_cost: Optional[float] = None
    actual_cost: Optional[float] = None
    error_message: Optional[str] = None

class Job(BaseModel):
    """Complete job model for database operations"""
    id: str
    status: JobStatus
    total_records: int = 0
    processed_records: int = 0
    failed_records: int = 0
    input_file_path: str
    output_file_path: Optional[str] = None
    options: Dict[str, Any] = Field(default_factory=dict)
    estimated_cost: float = 0.0
    actual_cost: float = 0.0
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    user_id: str = "default"
    error_message: Optional[str] = None
    processing_time_seconds: Optional[float] = None

class RecordStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    ENRICHED = "enriched"
    FAILED = "failed"
    SKIPPED = "skipped"

class Record(BaseModel):
    """Model for individual records within a job"""
    id: int
    job_id: str
    record_index: int
    status: RecordStatus
    original_data: Dict[str, Any]
    enriched_data: Optional[Dict[str, Any]] = None
    generated_content: Optional[Dict[str, Any]] = None
    processing_attempts: int = 0
    last_error: Optional[str] = None
    processing_time_ms: Optional[int] = None
    llm_tokens_used: Optional[int] = None
    cost: float = 0.0
    enrichment_confidence: Optional[float] = None
    data_completeness: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None