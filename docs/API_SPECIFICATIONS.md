# API Specifications - MVP Phase 1

## Base Configuration
- **Base URL**: `http://localhost:8000/api/v1`
- **Content-Type**: `application/json` (except file uploads)
- **Authentication**: Basic Auth (MVP), Bearer Token (Future)
- **Rate Limiting**: 100 requests per minute per IP

---

## 1. Job Management APIs

### 1.1 Create Enrichment Job
**POST** `/jobs/upload`

Upload CSV file and create enrichment job.

**Request**
```http
POST /api/v1/jobs/upload
Content-Type: multipart/form-data

file: [CSV file]
options: {
  "generate_variants": 3,
  "include_icebreaker": true,
  "include_hot_button": true
}
```

**CSV Format Requirements**
```csv
Company Name,Address,Phone,Email,Contact Name
"ABC Auto Sales","123 Main St, Miami, FL 33101","305-555-0100","info@abcauto.com","John Smith"
```

**Response**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Job created successfully",
  "total_records": 150,
  "estimated_completion_time": "2024-01-15T10:30:00Z",
  "webhook_url": "/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000/webhook"
}
```

**Error Responses**
- `400` - Invalid CSV format
- `413` - File too large (>10MB for MVP)
- `422` - Missing required columns

---

### 1.2 Get Job Status
**GET** `/jobs/{job_id}`

Check enrichment job status and progress.

**Request**
```http
GET /api/v1/jobs/550e8400-e29b-41d4-a716-446655440000
```

**Response**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": {
    "total_records": 150,
    "processed_records": 75,
    "failed_records": 2,
    "percentage": 50
  },
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T10:15:00Z",
  "estimated_completion": "2024-01-15T10:30:00Z",
  "errors": [
    {
      "record_id": 23,
      "error": "Unable to find website",
      "original_data": {"company": "XYZ Corp"}
    }
  ]
}
```

**Status Values**
- `pending` - Job created, not started
- `processing` - Currently enriching records
- `completed` - All records processed
- `failed` - Job failed (system error)
- `cancelled` - User cancelled job

---

### 1.3 Download Results
**GET** `/jobs/{job_id}/download`

Download enriched CSV file.

**Request**
```http
GET /api/v1/jobs/550e8400-e29b-41d4-a716-446655440000/download?format=csv
```

**Query Parameters**
- `format`: `csv` (default) or `json`
- `include_failed`: `true/false` - Include failed records

**Response (CSV)**
```csv
Company Name,Address,Phone,Email,Website,Owner First Name,Owner Last Name,Subject Line,Email Body,Hot Button
"ABC Auto Sales","123 Main St, Miami, FL","305-555-0100","info@abcauto.com","https://abcautosales.com","John","Smith","Increase your car sales by 30% this quarter","Hi John, I noticed ABC Auto Sales has been in Miami for 15 years...","Inventory management efficiency"
```

**Response (JSON)**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "enriched_records": [
    {
      "original": {
        "company_name": "ABC Auto Sales",
        "address": "123 Main St, Miami, FL",
        "phone": "305-555-0100",
        "email": "info@abcauto.com"
      },
      "enriched": {
        "website": "https://abcautosales.com",
        "owner_first_name": "John",
        "owner_last_name": "Smith",
        "owner_email": "john@abcautosales.com",
        "owner_phone": "305-555-0101"
      },
      "generated_content": {
        "subject_lines": [
          "Increase your car sales by 30% this quarter",
          "John, ready to transform ABC Auto Sales?",
          "The secret Miami dealers don't want you to know"
        ],
        "email_body": "Hi John, I noticed ABC Auto Sales...",
        "icebreaker": "I saw your recent review response on Google...",
        "hot_button": "Inventory management efficiency"
      }
    }
  ],
  "statistics": {
    "total_processed": 150,
    "successful": 148,
    "failed": 2,
    "average_enrichment_time": 2.3,
    "total_cost": 2.45
  }
}
```

---

### 1.4 List Jobs
**GET** `/jobs`

List all enrichment jobs for current user.

**Request**
```http
GET /api/v1/jobs?status=completed&limit=10&offset=0
```

**Query Parameters**
- `status`: Filter by status (pending/processing/completed/failed)
- `limit`: Records per page (default: 20, max: 100)
- `offset`: Pagination offset
- `sort`: `created_at` or `updated_at`
- `order`: `asc` or `desc`

**Response**
```json
{
  "jobs": [
    {
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "completed",
      "total_records": 150,
      "created_at": "2024-01-15T10:00:00Z",
      "completed_at": "2024-01-15T10:30:00Z"
    }
  ],
  "pagination": {
    "total": 45,
    "limit": 10,
    "offset": 0,
    "has_more": true
  }
}
```

---

### 1.5 Cancel Job
**DELETE** `/jobs/{job_id}`

Cancel a running enrichment job.

**Request**
```http
DELETE /api/v1/jobs/550e8400-e29b-41d4-a716-446655440000
```

**Response**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "cancelled",
  "message": "Job cancelled successfully",
  "processed_records": 75,
  "refund_eligible": false
}
```

---

## 2. Individual Record APIs (For Testing/Single Enrichment)

### 2.1 Enrich Single Record
**POST** `/enrich/single`

Enrich a single contact record synchronously.

**Request**
```json
{
  "company_name": "ABC Auto Sales",
  "address": "123 Main St, Miami, FL 33101",
  "phone": "305-555-0100",
  "email": "info@abcauto.com",
  "contact_name": "John Smith",
  "options": {
    "deep_search": true,
    "generate_variants": 3
  }
}
```

**Response**
```json
{
  "enriched_data": {
    "website": "https://abcautosales.com",
    "owner_first_name": "John",
    "owner_last_name": "Smith",
    "owner_email": "john@abcautosales.com",
    "linkedin": "https://linkedin.com/in/johnsmith",
    "company_size": "10-50",
    "year_founded": "2008"
  },
  "generated_content": {
    "subject_lines": [...],
    "email_body": "...",
    "icebreaker": "...",
    "hot_button": "..."
  },
  "enrichment_sources": [
    "web_search",
    "website_scrape",
    "llm_inference"
  ],
  "cost": 0.015,
  "processing_time": 3.2
}
```

---

## 3. Configuration APIs

### 3.1 Get Current Settings
**GET** `/settings`

**Response**
```json
{
  "llm_provider": "openai",
  "llm_model": "gpt-4o-mini",
  "max_concurrent_enrichments": 3,
  "features": {
    "web_search": true,
    "website_scraping": true,
    "linkedin_search": false,
    "email_variants": true
  },
  "cost_settings": {
    "cost_per_record_estimate": 0.015,
    "daily_spend_limit": 100.00
  }
}
```

---

### 3.2 Update Settings
**PATCH** `/settings`

**Request**
```json
{
  "llm_model": "gpt-3.5-turbo",
  "max_concurrent_enrichments": 5
}
```

---

## 4. Health & Monitoring APIs

### 4.1 Health Check
**GET** `/health`

**Response**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "database": "connected",
    "llm_api": "connected",
    "scraper": "ready"
  },
  "timestamp": "2024-01-15T10:00:00Z"
}
```

### 4.2 Get Usage Statistics
**GET** `/stats`

**Response**
```json
{
  "period": "last_24_hours",
  "records_processed": 1500,
  "total_cost": 22.50,
  "average_processing_time": 2.8,
  "success_rate": 0.97,
  "top_errors": [
    {
      "type": "website_not_found",
      "count": 23
    }
  ]
}
```

---

## Error Response Format

All error responses follow this structure:

```json
{
  "error": {
    "code": "INVALID_CSV_FORMAT",
    "message": "The uploaded CSV is missing required columns",
    "details": {
      "missing_columns": ["Company Name", "Address"],
      "provided_columns": ["Name", "Location", "Phone"]
    },
    "request_id": "req_abc123",
    "documentation_url": "https://docs.api.com/errors/INVALID_CSV_FORMAT"
  }
}
```

**Common Error Codes**
- `INVALID_CSV_FORMAT` - CSV formatting issues
- `RATE_LIMIT_EXCEEDED` - Too many requests
- `INSUFFICIENT_CREDITS` - Out of processing credits
- `LLM_API_ERROR` - LLM provider issue
- `SCRAPING_BLOCKED` - Website blocked scraping
- `RECORD_NOT_FOUND` - Cannot find company info
- `JOB_NOT_FOUND` - Invalid job ID
- `UNAUTHORIZED` - Authentication failed

---

## Webhook Events (Future)

### Job Completed Webhook
**POST** `{user_webhook_url}`

```json
{
  "event": "job.completed",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "summary": {
    "total_records": 150,
    "successful": 148,
    "failed": 2
  },
  "download_url": "https://api.example.com/api/v1/jobs/550e8400/download",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## Rate Limiting Headers

All responses include:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1673784000
```

---

## Authentication (MVP)

### Basic Authentication
```http
Authorization: Basic base64(username:password)
```

### Future: API Key Authentication
```http
X-API-Key: your_api_key_here
```

---

## CORS Configuration (for Web UI)

```python
# FastAPI CORS settings
ALLOWED_ORIGINS = [
    "http://localhost:3000",  # Development
    "https://app.yourdomain.com"  # Production
]
```