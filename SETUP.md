# AI Sales Agent - FastAPI Backend Setup

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Up Environment
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your OpenAI API key
# LLM_API_KEY=your_openai_api_key_here
```

### 3. Test Installation
```bash
python test_installation.py
```

### 4. Start the Server
```bash
python run_server.py
```

The API will be available at:
- **API Base**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health

## Manual Setup

### Alternative Server Start
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Initialize Database Manually
```bash
python -c "from app.db.connection import init_db; init_db()"
```

## API Endpoints

### Job Management
- `POST /api/v1/jobs/upload` - Upload CSV and create enrichment job
- `GET /api/v1/jobs/{job_id}` - Get job status and progress
- `GET /api/v1/jobs/{job_id}/download` - Download enriched results
- `GET /api/v1/jobs/` - List all jobs
- `DELETE /api/v1/jobs/{job_id}` - Cancel a job

### Health & Monitoring
- `GET /api/v1/health` - Basic health check
- `GET /api/v1/health/detailed` - Detailed system health

## File Structure

```
app/
├── __init__.py
├── main.py              # FastAPI application
├── config.py            # Settings and configuration
├── models/
│   ├── __init__.py
│   └── job.py           # Pydantic models
├── api/
│   ├── __init__.py
│   ├── jobs.py          # Job management endpoints
│   └── health.py        # Health check endpoints
└── db/
    ├── __init__.py
    └── connection.py     # Database setup and services

data/                    # SQLite database location
uploads/                 # Uploaded CSV files
outputs/                 # Generated result files
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_API_KEY` | OpenAI API key | Required |
| `LLM_PROVIDER` | LLM provider | `openai` |
| `LLM_MODEL` | Model name | `gpt-4o-mini` |
| `MAX_FILE_SIZE_MB` | Max upload size | `10` |
| `MAX_RECORDS_PER_JOB` | Max records per job | `10000` |
| `MAX_CONCURRENT_ENRICHMENTS` | Parallel processing limit | `3` |
| `DEBUG` | Enable debug mode | `false` |

## Testing the API

### Upload a CSV File
```bash
curl -X POST "http://localhost:8000/api/v1/jobs/upload" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@your_file.csv"
```

### Check Job Status
```bash
curl -X GET "http://localhost:8000/api/v1/jobs/{job_id}" \
     -H "accept: application/json"
```

### Download Results
```bash
curl -X GET "http://localhost:8000/api/v1/jobs/{job_id}/download?format=csv" \
     -o enriched_results.csv
```

## CSV Format Requirements

Your CSV file should contain at minimum:
- `Company Name` (required)
- `Address` (recommended)
- `Phone` (recommended)

Additional columns will be preserved in the output.

## Next Steps

This backend provides the foundation for:
1. **Enrichment Pipeline** - Connect to existing `auto_enrich` module
2. **AI Content Generation** - Implement LLM-powered email generation
3. **Web Interface** - Add React frontend for user-friendly interaction
4. **Advanced Features** - Caching, analytics, and performance optimization

## Development Mode

For development with auto-reload:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Database Schema

The application uses SQLite with the following tables:
- `jobs` - Enrichment job tracking
- `records` - Individual record processing
- `enrichment_cache` - Cache for API calls
- `email_templates` - Email template management
- `api_usage` - API usage tracking
- `settings` - Application settings

See `docs/DATABASE_SCHEMA.md` for complete schema details.