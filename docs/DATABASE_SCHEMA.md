# Database Schema Design - MVP Phase 1

## Database: SQLite (MVP) → PostgreSQL (Production)

---

## Core Tables

### 1. jobs
Tracks enrichment job status and metadata.

```sql
CREATE TABLE jobs (
    -- Primary Key
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    
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
    options TEXT DEFAULT '{}', -- JSON: {"generate_variants": 3, "deep_search": true}
    
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
    processing_time_seconds REAL
);

-- Indexes for common queries
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_user_id ON jobs(user_id);
CREATE INDEX idx_jobs_created_at ON jobs(created_at DESC);
```

---

### 2. records
Individual records within enrichment jobs.

```sql
CREATE TABLE records (
    -- Primary Key
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Job Reference
    job_id TEXT NOT NULL,
    record_index INTEGER NOT NULL, -- Position in original CSV
    
    -- Processing Status
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'enriched', 'failed', 'skipped')),
    
    -- Original Data (JSON)
    original_data TEXT NOT NULL, -- JSON: Complete original row
    
    -- Enriched Data (JSON)
    enriched_data TEXT, -- JSON: All discovered information
    
    -- Generated Content (JSON)
    generated_content TEXT, -- JSON: Email variants, subject lines, etc.
    
    -- Processing Metadata
    processing_attempts INTEGER DEFAULT 0,
    last_error TEXT,
    processing_time_ms INTEGER,
    llm_tokens_used INTEGER,
    cost REAL DEFAULT 0.0,
    
    -- Data Quality Scores
    enrichment_confidence REAL, -- 0.0 to 1.0
    data_completeness REAL, -- 0.0 to 1.0
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX idx_records_job_id ON records(job_id);
CREATE INDEX idx_records_status ON records(status);
CREATE INDEX idx_records_job_status ON records(job_id, status);
```

---

### 3. enrichment_cache
Cache to avoid duplicate API calls and reduce costs.

```sql
CREATE TABLE enrichment_cache (
    -- Primary Key
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Cache Key (what we're looking up)
    cache_key TEXT NOT NULL UNIQUE, -- Hash of company name + location
    lookup_type TEXT NOT NULL, -- 'website', 'contact', 'linkedin', etc.
    
    -- Cached Result
    result_data TEXT, -- JSON: Cached enrichment result
    
    -- Cache Metadata
    hit_count INTEGER DEFAULT 0,
    confidence_score REAL,
    source TEXT, -- 'web_search', 'scrape', 'llm_inference'
    
    -- Expiry
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP DEFAULT (datetime('now', '+7 days')),
    
    -- Indexes
    INDEX idx_cache_key ON enrichment_cache(cache_key),
    INDEX idx_cache_expires ON enrichment_cache(expires_at)
);

-- Cleanup expired cache entries
CREATE TRIGGER cleanup_expired_cache
    AFTER INSERT ON enrichment_cache
    BEGIN
        DELETE FROM enrichment_cache 
        WHERE expires_at < datetime('now')
        AND id % 100 = 0; -- Run cleanup every 100 inserts
    END;
```

---

### 4. email_templates
Store and version email templates.

```sql
CREATE TABLE email_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Template Identity
    name TEXT NOT NULL,
    template_type TEXT NOT NULL CHECK (template_type IN ('subject', 'body', 'icebreaker', 'hot_button')),
    
    -- Template Content
    template_text TEXT NOT NULL,
    variables TEXT, -- JSON: ["company_name", "owner_name", "city"]
    
    -- Usage Tracking
    usage_count INTEGER DEFAULT 0,
    success_rate REAL,
    
    -- Versioning
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT 1,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Track template performance
CREATE TABLE template_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id INTEGER NOT NULL,
    job_id TEXT NOT NULL,
    
    -- Metrics
    open_rate REAL,
    response_rate REAL,
    conversion_rate REAL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (template_id) REFERENCES email_templates(id),
    FOREIGN KEY (job_id) REFERENCES jobs(id)
);
```

---

### 5. api_usage
Track API usage for cost monitoring.

```sql
CREATE TABLE api_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- API Identity
    provider TEXT NOT NULL, -- 'openai', 'anthropic', 'duckduckgo'
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
);

-- Indexes for cost analysis
CREATE INDEX idx_api_usage_provider ON api_usage(provider);
CREATE INDEX idx_api_usage_created ON api_usage(created_at);
CREATE INDEX idx_api_usage_job ON api_usage(job_id);
```

---

### 6. settings
Key-value store for application settings.

```sql
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    value_type TEXT CHECK (value_type IN ('string', 'integer', 'float', 'boolean', 'json')),
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Default settings
INSERT INTO settings (key, value, value_type, description) VALUES
    ('llm_provider', 'openai', 'string', 'LLM provider to use'),
    ('llm_model', 'gpt-4o-mini', 'string', 'Model name'),
    ('max_concurrent_enrichments', '3', 'integer', 'Max parallel enrichments'),
    ('cache_ttl_days', '7', 'integer', 'Cache expiry in days'),
    ('daily_spend_limit', '100.0', 'float', 'Maximum daily API spend'),
    ('enable_deep_search', 'true', 'boolean', 'Enable deep web search');
```

---

## Future Tables (Phase 2+)

### 7. conversations (Phase 2)
```sql
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    record_id INTEGER NOT NULL,
    
    -- Conversation State
    current_state TEXT NOT NULL, -- 'outreach', 'qualifying', 'objection_handling', etc.
    conversation_history TEXT, -- JSON: Array of messages
    
    -- Extracted Information
    qualification_data TEXT, -- JSON: BANT/MEDDIC fields
    
    -- Metadata
    last_message_at TIMESTAMP,
    next_followup_at TIMESTAMP,
    
    FOREIGN KEY (record_id) REFERENCES records(id)
);
```

### 8. crm_integrations (Phase 3)
```sql
CREATE TABLE crm_integrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Integration Config
    crm_type TEXT NOT NULL, -- 'hubspot', 'pipedrive', 'gohighlevel'
    api_key TEXT NOT NULL, -- Encrypted
    webhook_url TEXT,
    
    -- Sync Settings
    sync_enabled BOOLEAN DEFAULT 1,
    last_sync_at TIMESTAMP,
    
    -- Field Mappings (JSON)
    field_mappings TEXT -- JSON: Maps our fields to CRM fields
);
```

---

## Views for Common Queries

### Job Summary View
```sql
CREATE VIEW job_summary AS
SELECT 
    j.id,
    j.status,
    j.total_records,
    j.processed_records,
    j.failed_records,
    ROUND(CAST(j.processed_records AS FLOAT) / j.total_records * 100, 2) as progress_percentage,
    j.actual_cost,
    j.created_at,
    j.completed_at,
    ROUND((julianday(j.completed_at) - julianday(j.started_at)) * 86400, 2) as processing_time_seconds
FROM jobs j;
```

### Daily Usage View
```sql
CREATE VIEW daily_usage AS
SELECT 
    DATE(created_at) as date,
    provider,
    COUNT(*) as api_calls,
    SUM(tokens_used) as total_tokens,
    SUM(cost) as total_cost,
    AVG(response_time_ms) as avg_response_time
FROM api_usage
GROUP BY DATE(created_at), provider;
```

### Record Success Rate View
```sql
CREATE VIEW enrichment_success_rate AS
SELECT 
    DATE(created_at) as date,
    COUNT(*) as total_records,
    SUM(CASE WHEN status = 'enriched' THEN 1 ELSE 0 END) as successful,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
    ROUND(CAST(SUM(CASE WHEN status = 'enriched' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100, 2) as success_rate
FROM records
WHERE status IN ('enriched', 'failed')
GROUP BY DATE(created_at);
```

---

## Migration Scripts

### SQLite to PostgreSQL Migration (Future)
```python
# migration.py
import sqlite3
import psycopg2
from datetime import datetime

def migrate_to_postgres():
    # Connect to SQLite
    sqlite_conn = sqlite3.connect('app.db')
    sqlite_cur = sqlite_conn.cursor()
    
    # Connect to PostgreSQL
    pg_conn = psycopg2.connect(
        "dbname=enrichment user=postgres password=secret"
    )
    pg_cur = pg_conn.cursor()
    
    # Create PostgreSQL schema with proper types
    pg_cur.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            status VARCHAR(20) NOT NULL,
            total_records INTEGER NOT NULL DEFAULT 0,
            -- ... rest of schema with PostgreSQL types
        )
    """)
    
    # Migrate data table by table
    tables = ['jobs', 'records', 'enrichment_cache', 'email_templates']
    
    for table in tables:
        sqlite_cur.execute(f"SELECT * FROM {table}")
        records = sqlite_cur.fetchall()
        
        for record in records:
            # Transform and insert into PostgreSQL
            pg_cur.execute(f"INSERT INTO {table} VALUES (%s, ...)", record)
    
    pg_conn.commit()
```

---

## Database Initialization Script

```python
# init_db.py
import sqlite3
from pathlib import Path

def init_database():
    """Initialize SQLite database with schema"""
    
    db_path = Path("data/app.db")
    db_path.parent.mkdir(exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    
    # Read and execute schema
    with open("schema.sql", "r") as f:
        schema = f.read()
        conn.executescript(schema)
    
    # Insert default settings
    conn.execute("""
        INSERT OR IGNORE INTO settings (key, value, value_type) 
        VALUES 
            ('llm_provider', 'openai', 'string'),
            ('llm_model', 'gpt-4o-mini', 'string'),
            ('max_concurrent_enrichments', '3', 'integer')
    """)
    
    conn.commit()
    conn.close()
    
    print(f"Database initialized at {db_path}")

if __name__ == "__main__":
    init_database()
```

---

## Query Examples

### Get Job with Progress
```sql
SELECT 
    j.*,
    COUNT(r.id) as total_records_actual,
    SUM(CASE WHEN r.status = 'enriched' THEN 1 ELSE 0 END) as enriched_count,
    SUM(CASE WHEN r.status = 'failed' THEN 1 ELSE 0 END) as failed_count
FROM jobs j
LEFT JOIN records r ON j.id = r.job_id
WHERE j.id = ?
GROUP BY j.id;
```

### Check Cache Before Enrichment
```sql
SELECT result_data 
FROM enrichment_cache 
WHERE cache_key = ? 
  AND lookup_type = ?
  AND expires_at > datetime('now')
LIMIT 1;
```

### Update Cache Hit Count
```sql
UPDATE enrichment_cache 
SET hit_count = hit_count + 1 
WHERE cache_key = ?;
```

### Get Cost Report
```sql
SELECT 
    DATE(created_at) as date,
    SUM(actual_cost) as daily_cost,
    COUNT(*) as jobs_processed,
    SUM(total_records) as records_processed
FROM jobs
WHERE status = 'completed'
  AND created_at >= datetime('now', '-30 days')
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

---

## Performance Considerations

1. **Indexes**: Created on all foreign keys and commonly queried columns
2. **JSON Storage**: Using TEXT with JSON for flexibility in MVP
3. **Cache Expiry**: Automatic cleanup trigger for expired cache
4. **Batch Operations**: Design supports bulk inserts for records
5. **Connection Pooling**: Use SQLite WAL mode for concurrent reads

```python
# Enable WAL mode for better concurrency
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA synchronous=NORMAL")
```

---

## Backup Strategy

```bash
# Simple SQLite backup
cp data/app.db data/backups/app_$(date +%Y%m%d_%H%M%S).db

# Automated daily backup cron job
0 2 * * * sqlite3 /app/data/app.db ".backup /app/data/backups/app_$(date +\%Y\%m\%d).db"
```