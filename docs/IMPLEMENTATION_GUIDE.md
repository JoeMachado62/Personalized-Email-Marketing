# Implementation Guide - Component Development

## Overview
This guide provides step-by-step implementation instructions for each component, enabling parallel development by multiple developers.

---

## Component Breakdown for Parallel Development

### Developer 1: Core API & Job Management
**Files to Create:**
- `app/main.py` - FastAPI application setup
- `app/api/jobs.py` - Job management endpoints
- `app/models/job.py` - Job data models
- `app/db/connection.py` - Database connection manager

### Developer 2: Enrichment Pipeline
**Files to Enhance/Create:**
- `auto_enrich/enricher.py` - Enhance existing
- `app/workers/enrichment_worker.py` - New async worker
- `app/services/cache_service.py` - Caching layer

### Developer 3: Web Interface & Frontend
**Files to Create:**
- `app/api/upload.py` - File upload handling
- `frontend/upload.html` - Simple upload UI
- `frontend/status.html` - Job status page
- `app/static/` - CSS/JS files

### Developer 4: AI & Content Generation
**Files to Create:**
- `app/services/llm_service.py` - LLM abstraction
- `app/services/content_generator.py` - Email generation
- `app/prompts/templates.py` - Prompt templates

---

## Component 1: FastAPI Application Setup

### File: `app/main.py`
```python
"""
Main FastAPI application entry point.
Handles application initialization, middleware setup, and route registration.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from app.db.connection import init_db
from app.api import jobs, upload, health
from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting application...")
    init_db()
    yield
    # Shutdown
    logger.info("Shutting down application...")

# Create FastAPI app
app = FastAPI(
    title="AI Sales Agent API",
    version="1.0.0",
    description="Autonomous email enrichment and generation platform",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["jobs"])
app.include_router(upload.router, prefix="/api/v1", tags=["upload"])
app.include_router(health.router, prefix="/api/v1", tags=["health"])

# Root endpoint
@app.get("/")
async def root():
    return {"message": "AI Sales Agent API", "version": "1.0.0"}
```

### File: `app/config.py`
```python
"""
Application configuration using Pydantic settings.
Loads from environment variables and .env file.
"""

from pydantic_settings import BaseSettings
from typing import List
from pathlib import Path

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "AI Sales Agent"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "sqlite:///./data/app.db"
    
    # API Keys
    LLM_API_KEY: str
    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = "gpt-4o-mini"
    
    # Limits
    MAX_CONCURRENT_ENRICHMENTS: int = 3
    MAX_FILE_SIZE_MB: int = 10
    MAX_RECORDS_PER_JOB: int = 10000
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # Paths
    UPLOAD_DIR: Path = Path("./uploads")
    OUTPUT_DIR: Path = Path("./outputs")
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

# Create directories
settings.UPLOAD_DIR.mkdir(exist_ok=True)
settings.OUTPUT_DIR.mkdir(exist_ok=True)
```

---

## Component 2: Job Management API

### File: `app/api/jobs.py`
```python
"""
Job management endpoints.
Handles CRUD operations for enrichment jobs.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
from uuid import uuid4
from app.models.job import Job, JobStatus, JobCreate, JobResponse
from app.db.connection import get_db
from app.services.job_service import JobService

router = APIRouter()

@router.post("/upload", response_model=JobResponse)
async def create_job(
    file: UploadFile,
    options: Optional[dict] = None,
    db = Depends(get_db)
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
    # Validate file size
    if file.size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(400, "File too large")
    
    # Save uploaded file
    job_id = str(uuid4())
    file_path = settings.UPLOAD_DIR / f"{job_id}.csv"
    
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    # Parse CSV to count records
    df = pd.read_csv(file_path)
    
    # Validate required columns
    required_columns = ['Company Name', 'Address', 'Phone']
    missing = set(required_columns) - set(df.columns)
    if missing:
        raise HTTPException(400, f"Missing columns: {missing}")
    
    # Create job in database
    job = JobService.create_job(
        job_id=job_id,
        total_records=len(df),
        input_file_path=str(file_path),
        options=options or {}
    )
    
    # Queue for processing
    from app.workers.enrichment_worker import process_job
    asyncio.create_task(process_job(job_id))
    
    return JobResponse(
        job_id=job_id,
        status="pending",
        message="Job created successfully",
        total_records=len(df)
    )

@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str, db = Depends(get_db)):
    """
    Get job status and progress.
    
    Returns:
    - Job status (pending/processing/completed/failed)
    - Progress percentage
    - Error details if failed
    """
    job = JobService.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        progress={
            "total_records": job.total_records,
            "processed_records": job.processed_records,
            "failed_records": job.failed_records,
            "percentage": (job.processed_records / job.total_records * 100) 
                         if job.total_records > 0 else 0
        },
        created_at=job.created_at,
        estimated_completion=job.estimated_completion
    )

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
    job = JobService.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    
    if job.status != "completed":
        raise HTTPException(400, f"Job is {job.status}, not completed")
    
    # Get enriched records
    records = JobService.get_enriched_records(job_id, include_failed)
    
    if format == "csv":
        # Generate CSV
        output_path = settings.OUTPUT_DIR / f"{job_id}_enriched.csv"
        df = pd.DataFrame(records)
        df.to_csv(output_path, index=False)
        
        return FileResponse(
            output_path,
            media_type="text/csv",
            filename=f"enriched_{job_id}.csv"
        )
    else:
        # Return JSON
        return {
            "job_id": job_id,
            "enriched_records": records,
            "statistics": {
                "total_processed": job.total_records,
                "successful": job.processed_records - job.failed_records,
                "failed": job.failed_records
            }
        }
```

---

## Component 3: Enrichment Worker

### File: `app/workers/enrichment_worker.py`
```python
"""
Asynchronous enrichment worker.
Processes records in parallel with rate limiting.
"""

import asyncio
from typing import List, Dict
from app.services.scraper_service import ScraperService
from app.services.llm_service import LLMService
from app.services.cache_service import CacheService
from app.db.connection import get_db

class EnrichmentWorker:
    def __init__(self, job_id: str, max_concurrent: int = 3):
        self.job_id = job_id
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.scraper = ScraperService()
        self.llm = LLMService()
        self.cache = CacheService()
    
    async def process_job(self, job_id: str):
        """
        Main entry point for job processing.
        
        Steps:
        1. Load job from database
        2. Parse input CSV
        3. Create record entries
        4. Process records in parallel
        5. Update job status
        """
        try:
            # Update job status to processing
            JobService.update_status(job_id, "processing")
            
            # Load records
            records = self.load_records(job_id)
            
            # Process in parallel with semaphore
            tasks = [
                self.enrich_record(record) 
                for record in records
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Save results
            self.save_results(results)
            
            # Update job status
            JobService.update_status(job_id, "completed")
            
        except Exception as e:
            JobService.update_status(job_id, "failed", error=str(e))
    
    async def enrich_record(self, record: Dict) -> Dict:
        """
        Enrich a single record.
        
        Pipeline:
        1. Check cache
        2. Search for website
        3. Scrape additional info
        4. Generate email content
        5. Update cache
        """
        async with self.semaphore:
            try:
                # Generate cache key
                cache_key = self.cache.generate_key(record)
                
                # Check cache
                cached = await self.cache.get(cache_key)
                if cached:
                    return cached
                
                # Step 1: Find website
                website = await self.scraper.find_website(
                    company_name=record['company_name'],
                    location=record.get('address', '')
                )
                
                # Step 2: Extract contact info
                if website:
                    contact_info = await self.scraper.extract_contact_info(website)
                else:
                    contact_info = {}
                
                # Step 3: Generate email content
                email_content = await self.llm.generate_email(
                    company_data=record,
                    website=website,
                    contact_info=contact_info
                )
                
                # Combine results
                enriched = {
                    **record,
                    'website': website,
                    **contact_info,
                    **email_content
                }
                
                # Cache result
                await self.cache.set(cache_key, enriched)
                
                return enriched
                
            except Exception as e:
                logger.error(f"Failed to enrich record: {e}")
                return {**record, 'error': str(e)}
```

---

## Component 4: LLM Service

### File: `app/services/llm_service.py`
```python
"""
LLM service abstraction.
Handles all AI content generation with provider abstraction.
"""

from abc import ABC, abstractmethod
from typing import Dict, List
import openai
from app.config import settings
from app.prompts.templates import EmailTemplates

class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        pass

class OpenAIProvider(LLMProvider):
    def __init__(self):
        openai.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL
    
    async def generate(self, prompt: str, temperature: float = 0.7) -> str:
        """Generate text using OpenAI API."""
        response = await openai.ChatCompletion.acreate(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=500
        )
        return response.choices[0].message.content

class LLMService:
    def __init__(self):
        # Factory pattern for provider selection
        if settings.LLM_PROVIDER == "openai":
            self.provider = OpenAIProvider()
        else:
            raise ValueError(f"Unknown provider: {settings.LLM_PROVIDER}")
        
        self.templates = EmailTemplates()
    
    async def generate_email(
        self,
        company_data: Dict,
        website: str = None,
        contact_info: Dict = None,
        variants: int = 3
    ) -> Dict:
        """
        Generate personalized email content.
        
        Returns:
        - subject_lines: List of subject line variants
        - email_body: Main email content
        - icebreaker: Personalized opening
        - hot_button: Key pain point to address
        """
        # Build context
        context = self.build_context(company_data, website, contact_info)
        
        # Generate subject lines
        subject_prompt = self.templates.get_subject_prompt(context)
        subject_lines = await self.generate_variants(subject_prompt, variants)
        
        # Generate email body
        body_prompt = self.templates.get_body_prompt(context)
        email_body = await self.provider.generate(body_prompt)
        
        # Generate icebreaker
        icebreaker_prompt = self.templates.get_icebreaker_prompt(context)
        icebreaker = await self.provider.generate(icebreaker_prompt)
        
        # Generate hot button
        hot_button_prompt = self.templates.get_hot_button_prompt(context)
        hot_button = await self.provider.generate(hot_button_prompt)
        
        return {
            "subject_lines": subject_lines,
            "email_body": email_body,
            "icebreaker": icebreaker,
            "hot_button": hot_button
        }
    
    async def generate_variants(self, prompt: str, count: int) -> List[str]:
        """Generate multiple variants of content."""
        tasks = [
            self.provider.generate(prompt, temperature=0.8)
            for _ in range(count)
        ]
        return await asyncio.gather(*tasks)
    
    def build_context(self, company_data: Dict, website: str, contact_info: Dict) -> Dict:
        """Build context for prompt generation."""
        return {
            "company_name": company_data.get("company_name"),
            "location": company_data.get("address", "").split(",")[1] if "," in company_data.get("address", "") else "",
            "website": website,
            "owner_name": contact_info.get("owner_name"),
            "industry": "automotive dealership",  # Can be enhanced
            "pain_points": self.infer_pain_points(company_data)
        }
    
    def infer_pain_points(self, company_data: Dict) -> List[str]:
        """Infer potential pain points from company data."""
        # This can be enhanced with more sophisticated analysis
        return [
            "inventory management",
            "lead generation",
            "customer retention",
            "online presence"
        ]
```

---

## Component 5: Prompt Templates

### File: `app/prompts/templates.py`
```python
"""
Prompt templates for email generation.
Maintains consistency and quality in AI outputs.
"""

class EmailTemplates:
    def get_subject_prompt(self, context: Dict) -> str:
        return f"""
        Create a compelling email subject line for {context['company_name']}, 
        a business in {context['location']}.
        
        Requirements:
        - Under 60 characters
        - Personalized to their business
        - Creates urgency or curiosity
        - Professional tone
        
        Context:
        - Website: {context.get('website', 'Not found')}
        - Industry: {context.get('industry', 'Unknown')}
        
        Generate ONE subject line:
        """
    
    def get_body_prompt(self, context: Dict) -> str:
        return f"""
        Write a personalized cold email for {context['company_name']}.
        
        Recipient: {context.get('owner_name', 'Business Owner')}
        Company: {context['company_name']}
        Location: {context['location']}
        Website: {context.get('website', 'No website found')}
        
        Requirements:
        - Start with personalized observation about their business
        - Identify a specific problem they likely face
        - Propose a solution (our service)
        - Include social proof or credibility
        - Clear call-to-action
        - 150-200 words maximum
        - Professional but conversational tone
        
        Email body:
        """
    
    def get_icebreaker_prompt(self, context: Dict) -> str:
        return f"""
        Create a personalized icebreaker opening for {context['company_name']}.
        
        This should be a specific observation about their business that shows
        you've done research. Reference something from their website, location,
        or industry.
        
        Website: {context.get('website')}
        Location: {context['location']}
        
        Write 1-2 sentences that feel genuine and specific:
        """
    
    def get_hot_button_prompt(self, context: Dict) -> str:
        return f"""
        Identify the most likely business challenge for {context['company_name']}.
        
        Industry: {context.get('industry')}
        Common pain points: {', '.join(context.get('pain_points', []))}
        
        Return ONE specific challenge they likely face, in 5-10 words:
        """
```

---

## Component 6: Simple Web Interface

### File: `frontend/index.html`
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Sales Agent - Enrichment Platform</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        
        .container {
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 600px;
            width: 100%;
        }
        
        h1 {
            color: #333;
            margin-bottom: 10px;
        }
        
        .subtitle {
            color: #666;
            margin-bottom: 30px;
        }
        
        .upload-area {
            border: 2px dashed #ddd;
            border-radius: 10px;
            padding: 40px;
            text-align: center;
            transition: all 0.3s;
            cursor: pointer;
        }
        
        .upload-area:hover {
            border-color: #667eea;
            background: #f8f9ff;
        }
        
        .upload-area.dragover {
            border-color: #667eea;
            background: #f0f2ff;
        }
        
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 16px;
            margin-top: 20px;
            transition: transform 0.2s;
        }
        
        .btn:hover {
            transform: translateY(-2px);
        }
        
        .status {
            margin-top: 20px;
            padding: 20px;
            border-radius: 10px;
            display: none;
        }
        
        .status.success {
            background: #d4edda;
            color: #155724;
            display: block;
        }
        
        .status.error {
            background: #f8d7da;
            color: #721c24;
            display: block;
        }
        
        .status.processing {
            background: #fff3cd;
            color: #856404;
            display: block;
        }
        
        .progress-bar {
            width: 100%;
            height: 20px;
            background: #e9ecef;
            border-radius: 10px;
            overflow: hidden;
            margin-top: 10px;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>AI Sales Agent</h1>
        <p class="subtitle">Upload your CSV to enrich contacts and generate personalized emails</p>
        
        <div class="upload-area" id="uploadArea">
            <svg width="60" height="60" viewBox="0 0 24 24" fill="none" stroke="#999" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="17 8 12 3 7 8"></polyline>
                <line x1="12" y1="3" x2="12" y2="15"></line>
            </svg>
            <p style="margin-top: 15px; color: #666;">Drop your CSV here or click to browse</p>
            <p style="margin-top: 5px; color: #999; font-size: 14px;">Maximum file size: 10MB</p>
            <input type="file" id="fileInput" accept=".csv" style="display: none;">
        </div>
        
        <button class="btn" id="uploadBtn" style="display: none;">Start Enrichment</button>
        
        <div class="status" id="status">
            <div id="statusMessage"></div>
            <div class="progress-bar" id="progressBar" style="display: none;">
                <div class="progress-fill" id="progressFill" style="width: 0%"></div>
            </div>
        </div>
    </div>
    
    <script>
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const uploadBtn = document.getElementById('uploadBtn');
        const status = document.getElementById('status');
        const statusMessage = document.getElementById('statusMessage');
        const progressBar = document.getElementById('progressBar');
        const progressFill = document.getElementById('progressFill');
        
        let selectedFile = null;
        
        // File selection
        uploadArea.addEventListener('click', () => fileInput.click());
        
        fileInput.addEventListener('change', (e) => {
            selectedFile = e.target.files[0];
            if (selectedFile) {
                uploadArea.innerHTML = `
                    <p style="color: #667eea; font-weight: bold;">${selectedFile.name}</p>
                    <p style="color: #999; font-size: 14px; margin-top: 5px;">
                        ${(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                `;
                uploadBtn.style.display = 'block';
            }
        });
        
        // Drag and drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            
            selectedFile = e.dataTransfer.files[0];
            if (selectedFile && selectedFile.name.endsWith('.csv')) {
                uploadArea.innerHTML = `
                    <p style="color: #667eea; font-weight: bold;">${selectedFile.name}</p>
                    <p style="color: #999; font-size: 14px; margin-top: 5px;">
                        ${(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                `;
                uploadBtn.style.display = 'block';
            }
        });
        
        // Upload handling
        uploadBtn.addEventListener('click', async () => {
            if (!selectedFile) return;
            
            const formData = new FormData();
            formData.append('file', selectedFile);
            
            try {
                // Upload file
                status.className = 'status processing';
                statusMessage.textContent = 'Uploading file...';
                progressBar.style.display = 'block';
                
                const response = await fetch('/api/v1/jobs/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    statusMessage.textContent = `Job created! Processing ${data.total_records} records...`;
                    
                    // Poll for status
                    pollJobStatus(data.job_id);
                } else {
                    throw new Error(data.error?.message || 'Upload failed');
                }
            } catch (error) {
                status.className = 'status error';
                statusMessage.textContent = `Error: ${error.message}`;
                progressBar.style.display = 'none';
            }
        });
        
        async function pollJobStatus(jobId) {
            const interval = setInterval(async () => {
                try {
                    const response = await fetch(`/api/v1/jobs/${jobId}`);
                    const data = await response.json();
                    
                    if (data.status === 'processing') {
                        const percentage = data.progress.percentage;
                        progressFill.style.width = `${percentage}%`;
                        statusMessage.textContent = `Processing: ${data.progress.processed_records}/${data.progress.total_records} records`;
                    } else if (data.status === 'completed') {
                        clearInterval(interval);
                        status.className = 'status success';
                        statusMessage.innerHTML = `
                            Enrichment complete! 
                            <a href="/api/v1/jobs/${jobId}/download" 
                               style="color: #667eea; font-weight: bold;">
                               Download Results
                            </a>
                        `;
                        progressBar.style.display = 'none';
                    } else if (data.status === 'failed') {
                        clearInterval(interval);
                        status.className = 'status error';
                        statusMessage.textContent = 'Job failed. Please try again.';
                        progressBar.style.display = 'none';
                    }
                } catch (error) {
                    clearInterval(interval);
                    status.className = 'status error';
                    statusMessage.textContent = 'Error checking status';
                }
            }, 2000); // Poll every 2 seconds
        }
    </script>
</body>
</html>
```

---

## Development Task Assignment

### Sprint 1 (Week 1): Foundation
**All Developers Together:**
- Set up project structure
- Configure environment
- Initialize database

**Then Split:**

| Developer | Tasks | Deliverables |
|-----------|-------|--------------|
| Dev 1 | FastAPI setup, Job APIs | Working `/upload`, `/status` endpoints |
| Dev 2 | Enhance enricher.py, Create worker | Basic enrichment pipeline |
| Dev 3 | HTML upload interface | File upload UI |
| Dev 4 | LLM service setup | Email generation working |

### Sprint 2 (Week 2): Integration
| Developer | Tasks | Deliverables |
|-----------|-------|--------------|
| Dev 1 | Download API, error handling | Complete job lifecycle |
| Dev 2 | Cache service, optimization | Faster enrichment |
| Dev 3 | Status page, progress tracking | Full UI flow |
| Dev 4 | Prompt refinement, variants | Better email quality |

### Sprint 3 (Week 3): Polish & Deploy
**All Developers:**
- Integration testing
- Bug fixes
- Performance optimization
- Docker deployment
- Documentation

---

## Testing Checklist

### Unit Tests (Each Developer)
```python
# test_job_api.py
def test_create_job():
    # Test job creation with valid CSV
    
def test_invalid_csv():
    # Test rejection of invalid format

# test_enrichment.py  
def test_website_discovery():
    # Test scraper finds correct website
    
def test_email_generation():
    # Test LLM generates valid content

# test_cache.py
def test_cache_hit():
    # Test cache returns stored data
```

### Integration Tests (Team)
```python
def test_full_pipeline():
    # Upload CSV → Process → Download results
    
def test_concurrent_jobs():
    # Multiple jobs processing simultaneously
    
def test_error_recovery():
    # Job continues after individual record failure
```

### Load Tests
```python
# Use Locust for load testing
def test_10k_records():
    # Process Florida dealer dataset
    # Target: < 30 minutes
    # Cost: < $200
```

---

## Quick Start for Each Developer

### Developer 1 (API)
```bash
pip install fastapi uvicorn aiofiles pandas
python -m app.main
# API docs at http://localhost:8000/docs
```

### Developer 2 (Enrichment)
```bash
pip install playwright httpx
playwright install
python -m app.workers.enrichment_worker
```

### Developer 3 (Frontend)
```bash
# Simply open frontend/index.html in browser
# Or serve with: python -m http.server 3000
```

### Developer 4 (AI)
```bash
pip install openai
export LLM_API_KEY=your_key
python -m app.services.llm_service
```

---

This implementation guide provides everything needed for parallel development. Each developer can work independently on their component, with clear interfaces for integration.