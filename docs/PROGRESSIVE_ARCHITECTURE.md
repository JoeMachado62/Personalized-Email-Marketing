# Progressive Architecture Design: AI Sales Agent Platform

## Architecture Philosophy
Build a modular, extensible system that starts simple (MVP) and progressively adds sophistication without requiring major refactoring. Each phase builds upon the previous foundation.

---

## Phase 1: MVP - Core Enrichment & Email Generation
**Goal**: Ship in 2-3 weeks with basic CSV enrichment and email generation

### System Components

```
┌─────────────────────────────────────────────┐
│         Simple Web Interface (FastAPI)       │
│              - CSV Upload/Download           │
│              - Job Status Tracking           │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│           Job Orchestrator                   │
│         (Python Async/Threading)             │
└────────────────┬────────────────────────────┘
                 │
     ┌───────────┼───────────┬──────────────┐
     ▼           ▼           ▼              ▼
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│Scraper  │ │Search   │ │AI Engine│ │Storage  │
│Module   │ │Module   │ │Module   │ │Module   │
│         │ │         │ │         │ │         │
│Playwright│ │DuckDuck │ │LLM API  │ │SQLite   │
└─────────┘ └─────────┘ └─────────┘ └─────────┘
```

### Core Modules

#### 1. Web Interface (FastAPI)
```python
# Simple endpoints for MVP
POST /api/jobs/upload     # Upload CSV, return job_id
GET  /api/jobs/{job_id}   # Check status
GET  /api/jobs/{job_id}/download  # Get enriched CSV
```

#### 2. Job Orchestrator
```python
class EnrichmentJob:
    def __init__(self, csv_data):
        self.id = uuid4()
        self.status = "pending"
        self.records = parse_csv(csv_data)
        
    async def process(self):
        # Simple sequential processing for MVP
        for record in self.records:
            enriched = await self.enrich_record(record)
            self.save_result(enriched)
```

#### 3. Enrichment Pipeline (Existing + Enhanced)
```python
# Leverage existing auto_enrich modules
class EnrichmentPipeline:
    async def enrich(self, record):
        # Step 1: Web search for company
        website = await scraper.find_website(record)
        
        # Step 2: Extract additional info
        contact_info = await scraper.extract_info(website)
        
        # Step 3: Generate personalized email
        email_content = await ai_engine.generate_email(
            record + website + contact_info
        )
        
        return EnrichedRecord(record, email_content)
```

#### 4. Data Storage (SQLite for MVP)
```sql
-- Simple schema for MVP
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    status TEXT,
    created_at TIMESTAMP,
    total_records INTEGER,
    processed_records INTEGER
);

CREATE TABLE enriched_records (
    id INTEGER PRIMARY KEY,
    job_id TEXT,
    original_data JSON,
    enriched_data JSON,
    email_subject TEXT,
    email_body TEXT,
    created_at TIMESTAMP
);
```

### Technology Stack (MVP)
- **Backend**: Python 3.11+ (existing codebase compatible)
- **Web Framework**: FastAPI (async support, automatic API docs)
- **Database**: SQLite (zero config, file-based)
- **Queue**: Python asyncio (built-in, no Redis needed yet)
- **Scraping**: Playwright (already implemented)
- **Search**: DuckDuckGo API (already implemented)
- **LLM**: OpenAI/Anthropic API (configurable)
- **Deployment**: Single Docker container or Python venv

### MVP Deployment
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN playwright install chromium
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Phase 2: Conversation Management
**Goal**: Add autonomous email conversation handling

### New Components
```
┌─────────────────────────────────────────────┐
│          Email Service Integration           │
│         (IMAP/SMTP or Webhook)              │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│         Conversation State Machine           │
│      (Redis for State Persistence)          │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│         Response Classifier                  │
│    (Intent Detection & Routing)             │
└──────────────────────────────────────────────┘
```

### Conversation State Machine
```python
class ConversationStateMachine:
    states = {
        'initial_outreach': InitialOutreachState,
        'awaiting_response': AwaitingResponseState,
        'qualifying': QualifyingState,
        'objection_handling': ObjectionHandlingState,
        'scheduling': SchedulingState,
        'nurture': NurtureState
    }
    
    async def process_email(self, email, context):
        current_state = self.get_state(context.conversation_id)
        intent = await self.classify_intent(email)
        next_state = current_state.transition(intent)
        response = await next_state.generate_response(context)
        return response
```

### State Persistence (Redis)
```python
# Conversation context stored in Redis
{
    "conversation_id": "uuid",
    "contact_id": "uuid",
    "current_state": "qualifying",
    "history": [...],
    "extracted_info": {
        "budget": null,
        "timeline": "Q2",
        "decision_maker": true
    }
}
```

---

## Phase 3: CRM Integrations
**Goal**: Bi-directional sync with major CRMs

### Integration Architecture
```
┌─────────────────────────────────────────────┐
│            CRM Adapter Layer                 │
│         (Strategy Pattern)                   │
├──────────┬──────────┬──────────┬───────────┤
│HubSpot   │Pipedrive │GoHighLevel│Salesforce│
│Adapter   │Adapter   │Adapter   │Adapter   │
└──────────┴──────────┴──────────┴───────────┘
```

### Adapter Pattern
```python
class CRMAdapter(ABC):
    @abstractmethod
    async def sync_contact(self, contact): pass
    
    @abstractmethod
    async def update_activity(self, activity): pass
    
    @abstractmethod
    async def handle_webhook(self, payload): pass

class HubSpotAdapter(CRMAdapter):
    async def sync_contact(self, contact):
        # HubSpot-specific implementation
        pass
```

### Webhook Registry
```python
# Dynamic webhook routing
POST /webhooks/hubspot
POST /webhooks/pipedrive
POST /webhooks/gohighlevel
```

---

## Phase 4: Full Web UI & Analytics
**Goal**: Professional SaaS-like interface

### Frontend Architecture
```
┌─────────────────────────────────────────────┐
│          React/Vue.js Dashboard              │
├─────────────────────────────────────────────┤
│ Campaign Manager │ Contact Explorer │Analytics│
└─────────────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────┐
│            GraphQL Gateway                   │
│      (Aggregates Multiple APIs)             │
└──────────────────────────────────────────────┘
```

---

## Extension Points & Interfaces

### 1. Enrichment Sources (Plugin System)
```python
class EnrichmentSource(ABC):
    @abstractmethod
    async def enrich(self, record): pass

# Easy to add new sources
class LinkedInSource(EnrichmentSource): pass
class TwitterSource(EnrichmentSource): pass
class CustomAPISource(EnrichmentSource): pass
```

### 2. LLM Providers (Strategy Pattern)
```python
class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt): pass

class OpenAIProvider(LLMProvider): pass
class AnthropicProvider(LLMProvider): pass
class LocalLLMProvider(LLMProvider): pass  # Ollama
```

### 3. Storage Backends (Repository Pattern)
```python
class StorageBackend(ABC):
    @abstractmethod
    async def save(self, data): pass
    
    @abstractmethod
    async def retrieve(self, id): pass

class SQLiteBackend(StorageBackend): pass
class PostgresBackend(StorageBackend): pass
class MongoBackend(StorageBackend): pass
```

---

## API Design (RESTful + Webhooks)

### Core MVP APIs
```yaml
# Phase 1 - MVP
/api/v1/jobs:
  POST: Upload CSV and start enrichment
  GET: List all jobs
  
/api/v1/jobs/{job_id}:
  GET: Get job status and progress
  DELETE: Cancel job
  
/api/v1/jobs/{job_id}/results:
  GET: Download enriched CSV

# Phase 2 - Conversations
/api/v1/conversations:
  GET: List all conversations
  POST: Start new conversation
  
/api/v1/conversations/{id}/messages:
  GET: Get conversation history
  POST: Send message

# Phase 3 - CRM
/api/v1/integrations:
  GET: List configured integrations
  POST: Add new integration
  
/api/v1/webhooks/{provider}:
  POST: Receive CRM webhooks
```

---

## Data Flow Architecture

### MVP Data Flow
```
1. User uploads CSV
2. System creates job with unique ID
3. For each record:
   a. Search for company website
   b. Scrape additional info
   c. Generate personalized email via LLM
   d. Store enriched record
4. User downloads enriched CSV
```

### Full System Data Flow (Phase 4)
```
1. Contact enters system (CSV/CRM/API)
2. Enrichment pipeline activates
3. Initial email sent
4. Response received via webhook/IMAP
5. Conversation engine processes
6. Next action determined
7. CRM updated
8. Analytics tracked
9. Human handoff if needed
```

---

## Configuration Management

### Environment Variables (MVP)
```env
# Core Settings
APP_ENV=development
API_PORT=8000
DATABASE_URL=sqlite:///./app.db

# LLM Configuration
LLM_PROVIDER=openai
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
LLM_MAX_TOKENS=500
LLM_TEMPERATURE=0.7

# Scraping
PLAYWRIGHT_HEADLESS=true
SEARCH_PROVIDER=duckduckgo
MAX_CONCURRENT_SCRAPES=3

# Phase 2+ Settings
REDIS_URL=redis://localhost:6379
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
```

### Feature Flags
```python
FEATURES = {
    'conversation_management': False,  # Phase 2
    'crm_integration': False,          # Phase 3
    'advanced_analytics': False,       # Phase 4
    'bulk_processing': True,           # MVP
    'email_variants': True,            # MVP
}
```

---

## Performance Considerations

### MVP Targets
- Process 100 records in < 5 minutes
- Handle 10 concurrent enrichment jobs
- < 500ms API response time
- SQLite can handle up to 100K records

### Scaling Strategy (Post-MVP)
1. **Phase 2**: Add Redis for queue/cache
2. **Phase 3**: PostgreSQL for production
3. **Phase 4**: Horizontal scaling with Kubernetes

### Cost Optimization
```python
class CostOptimizer:
    def __init__(self):
        self.cache = TTLCache(maxsize=1000, ttl=3600)
    
    async def get_enrichment(self, company_name):
        # Check cache first
        if company_name in self.cache:
            return self.cache[company_name]
        
        # Use cheaper models for simple tasks
        if self.is_simple_enrichment(company_name):
            result = await self.use_cheap_model()
        else:
            result = await self.use_expensive_model()
        
        self.cache[company_name] = result
        return result
```

---

## Security Architecture

### MVP Security
- Input validation on CSV uploads
- Rate limiting on API endpoints
- Secure storage of API keys
- Basic authentication for web interface

### Production Security (Phase 2+)
- OAuth2/JWT authentication
- Role-based access control
- Encrypted data at rest
- API key rotation
- Audit logging
- GDPR compliance tools

---

## Development Roadmap

### Week 1-2: MVP Core
- [ ] Set up FastAPI project structure
- [ ] Integrate existing enrichment modules
- [ ] Build simple web interface
- [ ] Implement CSV upload/download
- [ ] Add SQLite storage

### Week 3: MVP Polish
- [ ] Error handling and retry logic
- [ ] Progress tracking
- [ ] Basic deployment (Docker)
- [ ] Documentation
- [ ] Testing with 10K dealer dataset

### Month 2: Phase 2
- [ ] Conversation state machine
- [ ] Email integration
- [ ] Response classification
- [ ] Redis integration

### Month 3: Phase 3
- [ ] CRM adapters
- [ ] Webhook handling
- [ ] Bi-directional sync

### Month 4: Phase 4
- [ ] React/Vue dashboard
- [ ] Analytics engine
- [ ] Advanced features

---

## Testing Strategy

### MVP Testing
```python
# Simple pytest structure
tests/
  test_enrichment.py
  test_api.py
  test_scraper.py
  
# Key test cases
def test_csv_upload():
    # Test file upload and job creation
    
def test_enrichment_pipeline():
    # Test single record enrichment
    
def test_concurrent_jobs():
    # Test multiple simultaneous jobs
```

### Load Testing
```bash
# Use locust for load testing
locust -f loadtest.py --host=http://localhost:8000 \
       --users=10 --spawn-rate=2
```

---

## Deployment Options

### Option 1: Single VPS (MVP)
```bash
# Simple deployment on $20/month VPS
git clone repo
python -m venv venv
pip install -r requirements.txt
playwright install
uvicorn app.main:app --host 0.0.0.0
```

### Option 2: Docker Compose (Recommended)
```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///./data/app.db
    volumes:
      - ./data:/app/data
```

### Option 3: Cloud Native (Future)
- AWS ECS/Fargate
- Google Cloud Run
- Azure Container Instances

---

## Success Metrics

### MVP Success Criteria
- Successfully enrich 10,000 records
- < $0.02 per record in LLM costs
- 95% uptime
- < 1% error rate
- Positive user feedback from pilot users

### Long-term Success Metrics
- CAC < $100
- Churn < 5% monthly
- NPS > 50
- Process 1M records/month
- 50+ CRM integrations