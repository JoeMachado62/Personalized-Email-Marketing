"""
SQLite database connection and initialization.
Sets up the database schema and provides connection management.
"""

import sqlite3
import json
import logging
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, Dict, Any, List
from app.config import settings

logger = logging.getLogger(__name__)

DATABASE_PATH = settings.DATA_DIR / "app.db"

def init_db():
    """Initialize SQLite database with complete schema"""
    logger.info(f"Initializing database at {DATABASE_PATH}")
    
    # Ensure data directory exists
    DATABASE_PATH.parent.mkdir(exist_ok=True)
    
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    
    # Create all tables
    create_tables(conn)
    
    # Insert default settings
    insert_default_settings(conn)
    
    conn.close()
    logger.info("Database initialization complete")

def create_tables(conn: sqlite3.Connection):
    """Create all database tables"""
    
    # Jobs table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            -- Primary Key
            id TEXT PRIMARY KEY,
            
            -- Job Status
            status TEXT NOT NULL DEFAULT 'pending' 
                CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')),
            
            -- Record Counts
            total_records INTEGER NOT NULL DEFAULT 0,
            processed_records INTEGER NOT NULL DEFAULT 0,
            failed_records INTEGER NOT NULL DEFAULT 0,
            
            -- File References
            input_file_path TEXT NOT NULL,
            output_file_path TEXT,
            
            -- Job Options (JSON)
            options TEXT DEFAULT '{}',
            
            -- Cost Tracking
            estimated_cost REAL DEFAULT 0.0,
            actual_cost REAL DEFAULT 0.0,
            
            -- Timestamps
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            
            -- User Reference (for multi-tenant future)
            user_id TEXT DEFAULT 'default',
            
            -- Metadata
            error_message TEXT,
            processing_time_seconds REAL,
            progress_percentage REAL DEFAULT 0.0
        )
    """)
    
    # Records table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS records (
            -- Primary Key
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- Job Reference
            job_id TEXT NOT NULL,
            record_index INTEGER NOT NULL,
            
            -- Processing Status
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'processing', 'enriched', 'failed', 'skipped')),
            
            -- Original Data (JSON)
            original_data TEXT NOT NULL,
            
            -- Enriched Data (JSON)
            enriched_data TEXT,
            
            -- Generated Content (JSON)
            generated_content TEXT,
            
            -- Processing Metadata
            processing_attempts INTEGER DEFAULT 0,
            last_error TEXT,
            processing_time_ms INTEGER,
            llm_tokens_used INTEGER,
            cost REAL DEFAULT 0.0,
            
            -- Data Quality Scores
            enrichment_confidence REAL,
            data_completeness REAL,
            
            -- Timestamps
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP,
            
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
        )
    """)
    
    # Enrichment cache table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS enrichment_cache (
            -- Primary Key
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- Cache Key (what we're looking up)
            cache_key TEXT NOT NULL UNIQUE,
            lookup_type TEXT NOT NULL,
            
            -- Cached Result
            result_data TEXT,
            
            -- Cache Metadata
            hit_count INTEGER DEFAULT 0,
            confidence_score REAL,
            source TEXT,
            
            -- Expiry
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP DEFAULT (datetime('now', '+7 days'))
        )
    """)
    
    # Email templates table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS email_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- Template Identity
            name TEXT NOT NULL,
            template_type TEXT NOT NULL CHECK (template_type IN ('subject', 'body', 'icebreaker', 'hot_button')),
            
            -- Template Content
            template_text TEXT NOT NULL,
            variables TEXT,
            
            -- Usage Tracking
            usage_count INTEGER DEFAULT 0,
            success_rate REAL,
            
            -- Versioning
            version INTEGER DEFAULT 1,
            is_active BOOLEAN DEFAULT 1,
            
            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # API usage table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS api_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- API Identity
            provider TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            
            -- Usage Details
            job_id TEXT,
            record_id INTEGER,
            
            -- Metrics
            tokens_used INTEGER,
            cost REAL NOT NULL,
            response_time_ms INTEGER,
            status_code INTEGER,
            
            -- Request/Response (for debugging)
            request_size_bytes INTEGER,
            response_size_bytes INTEGER,
            error_message TEXT,
            
            -- Timestamp
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
            FOREIGN KEY (record_id) REFERENCES records(id) ON DELETE CASCADE
        )
    """)
    
    # Settings table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            value_type TEXT CHECK (value_type IN ('string', 'integer', 'float', 'boolean', 'json')),
            description TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create indexes
    create_indexes(conn)
    
    # Create triggers
    create_triggers(conn)
    
    conn.commit()

def create_indexes(conn: sqlite3.Connection):
    """Create database indexes for performance"""
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)",
        "CREATE INDEX IF NOT EXISTS idx_jobs_user_id ON jobs(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_records_job_id ON records(job_id)",
        "CREATE INDEX IF NOT EXISTS idx_records_status ON records(status)",
        "CREATE INDEX IF NOT EXISTS idx_records_job_status ON records(job_id, status)",
        "CREATE INDEX IF NOT EXISTS idx_cache_key ON enrichment_cache(cache_key)",
        "CREATE INDEX IF NOT EXISTS idx_cache_expires ON enrichment_cache(expires_at)",
        "CREATE INDEX IF NOT EXISTS idx_api_usage_provider ON api_usage(provider)",
        "CREATE INDEX IF NOT EXISTS idx_api_usage_created ON api_usage(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_api_usage_job ON api_usage(job_id)"
    ]
    
    for index in indexes:
        conn.execute(index)

def create_triggers(conn: sqlite3.Connection):
    """Create database triggers"""
    # Cleanup expired cache entries
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS cleanup_expired_cache
            AFTER INSERT ON enrichment_cache
            BEGIN
                DELETE FROM enrichment_cache 
                WHERE expires_at < datetime('now')
                AND id % 100 = 0;
            END
    """)

def insert_default_settings(conn: sqlite3.Connection):
    """Insert default application settings"""
    default_settings = [
        ('llm_provider', 'openai', 'string', 'LLM provider to use'),
        ('llm_model', 'gpt-4o-mini', 'string', 'Model name'),
        ('max_concurrent_enrichments', '3', 'integer', 'Max parallel enrichments'),
        ('cache_ttl_days', '7', 'integer', 'Cache expiry in days'),
        ('daily_spend_limit', '100.0', 'float', 'Maximum daily API spend'),
        ('enable_deep_search', 'true', 'boolean', 'Enable deep web search')
    ]
    
    for key, value, value_type, description in default_settings:
        conn.execute("""
            INSERT OR IGNORE INTO settings (key, value, value_type, description) 
            VALUES (?, ?, ?, ?)
        """, (key, value, value_type, description))
    
    conn.commit()

@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Enable dict-like row access
    conn.execute("PRAGMA foreign_keys = ON")
    
    try:
        yield conn
    finally:
        conn.close()

class JobService:
    """Service class for job-related database operations"""
    
    @staticmethod
    def create_job(job_id: str, total_records: int, input_file_path: str, options: Dict[str, Any] = None) -> str:
        """Create a new job in the database"""
        if options is None:
            options = {}
        
        with get_db() as conn:
            conn.execute("""
                INSERT INTO jobs (id, total_records, input_file_path, options)
                VALUES (?, ?, ?, ?)
            """, (job_id, total_records, input_file_path, json.dumps(options)))
            conn.commit()
            
        return job_id
    
    @staticmethod
    def get_job(job_id: str) -> Optional[Dict[str, Any]]:
        """Get job by ID"""
        with get_db() as conn:
            cursor = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            
            if row:
                job = dict(row)
                job['options'] = json.loads(job['options'] or '{}')
                return job
            return None
    
    @staticmethod
    def update_status(job_id: str, status: str, error: Optional[str] = None):
        """Update job status"""
        with get_db() as conn:
            if error:
                conn.execute("""
                    UPDATE jobs 
                    SET status = ?, error_message = ?, 
                        started_at = CASE WHEN status = 'pending' THEN CURRENT_TIMESTAMP ELSE started_at END,
                        completed_at = CASE WHEN ? IN ('completed', 'failed', 'cancelled') THEN CURRENT_TIMESTAMP ELSE completed_at END
                    WHERE id = ?
                """, (status, error, status, job_id))
            else:
                conn.execute("""
                    UPDATE jobs 
                    SET status = ?,
                        started_at = CASE WHEN status = 'pending' AND ? = 'processing' THEN CURRENT_TIMESTAMP ELSE started_at END,
                        completed_at = CASE WHEN ? IN ('completed', 'failed', 'cancelled') THEN CURRENT_TIMESTAMP ELSE completed_at END
                    WHERE id = ?
                """, (status, status, status, job_id))
            conn.commit()
    
    @staticmethod
    def update_progress(job_id: str, processed: int, failed: int):
        """Update job progress"""
        with get_db() as conn:
            conn.execute("""
                UPDATE jobs 
                SET processed_records = ?, failed_records = ?
                WHERE id = ?
            """, (processed, failed, job_id))
            conn.commit()
    
    @staticmethod
    def update_job(job_id: str, updates: Dict[str, Any]):
        """Update job with arbitrary fields"""
        with get_db() as conn:
            # Build dynamic update query
            set_clauses = []
            values = []
            
            for key, value in updates.items():
                if key in ['started_at', 'completed_at', 'output_file_path', 'error_message',
                          'processed_records', 'failed_records', 'actual_cost', 'progress_percentage']:
                    set_clauses.append(f"{key} = ?")
                    values.append(value)
            
            if set_clauses:
                query = f"UPDATE jobs SET {', '.join(set_clauses)} WHERE id = ?"
                values.append(job_id)
                conn.execute(query, values)
                conn.commit()
    
    @staticmethod
    def get_enriched_records(job_id: str, include_failed: bool = False) -> List[Dict[str, Any]]:
        """Get enriched records for a job"""
        with get_db() as conn:
            if include_failed:
                cursor = conn.execute("""
                    SELECT * FROM records 
                    WHERE job_id = ? AND status IN ('enriched', 'failed')
                    ORDER BY record_index
                """, (job_id,))
            else:
                cursor = conn.execute("""
                    SELECT * FROM records 
                    WHERE job_id = ? AND status = 'enriched'
                    ORDER BY record_index
                """, (job_id,))
            
            records = []
            for row in cursor.fetchall():
                record = dict(row)
                record['original_data'] = json.loads(record['original_data'])
                if record['enriched_data']:
                    record['enriched_data'] = json.loads(record['enriched_data'])
                if record['generated_content']:
                    record['generated_content'] = json.loads(record['generated_content'])
                records.append(record)
            
            return records