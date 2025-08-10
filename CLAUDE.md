# CLAUDE.md - Orchestration Document

## IMPORTANT INSTRUCTIONS FOR CLAUDE CODE

### Development Guidelines
1. **EXPLORATORY DISCUSSIONS FIRST**: When the user is discussing ideas, architecture, or exploring possibilities, DO NOT immediately implement code changes. Instead:
   - Discuss the approach and implications
   - Present options and trade-offs
   - Wait for explicit approval before implementing
   - Use phrases like "Would you like me to implement this?" or "Should I proceed with these changes?"

2. **COST CONSIDERATIONS**: 
   - Always consider API costs and token usage in solutions
   - Prefer free/low-cost alternatives when available
   - Clearly communicate when a solution involves ongoing costs
   - Implement costly features as optional/fallback mechanisms

3. **MCP SERVER USAGE**:
   - Fetch MCP: Use freely as it has NO token costs (just HTML→Markdown conversion)
   - Exa MCP: Reserve for development/research assistance, NOT production code
   - Always implement fallbacks for any external service

## System Overview
An AI-powered universal enrichment platform that transforms CSV business data into comprehensive profiles with personalized marketing content. This orchestration document guides the system architecture and references detailed implementation documentation.

## Quick Start
```bash
# Install core dependencies
pip install -r requirements.txt

# Configure API keys and MCP
cp .env.example .env
vim .env  # Add LLM_API_KEY, enable ENABLE_MCP_FETCH=true

# Run enrichment
python -m auto_enrich.enricher --input data.csv --output enriched.csv
```

## System Architecture

### Enrichment Pipeline Flow
```
CSV Input → Campaign Context → Search Optimization → Data Collection → 
Profile Building → Content Generation → Enriched CSV Output
```

### Core Components

#### 1. Search & Discovery Layer
**Module**: `auto_enrich/search_query_optimizer.py`  
**Primary Implementation**: `auto_enrich/search_with_selenium.py` (Real Chrome Browser)
**Documentation**: [docs/search-optimization.md](docs/search-optimization.md)
- Intelligent query construction
- Real Chrome browser search (no bot detection)
- Google My Business panel extraction
- Clean search result processing

#### 2. Data Collection Layer
**Primary Module**: `auto_enrich/web_scraper_selenium.py` (Selenium + MCP)
**MCP Integration**: `auto_enrich/mcp_client.py` (HTML→Markdown)
**Documentation**: [docs/data-collection.md](docs/data-collection.md)
- Selenium-based web scraping with real Chrome browser
- MCP Fetch HTML-to-Markdown conversion (no API costs)
- Contact information extraction from clean Markdown
- Social media discovery and business directory mining

#### 3. Profile Building Layer
**Module**: `auto_enrich/data_interpreter.py`  
**Documentation**: [docs/profile-building.md](docs/profile-building.md)
- AI-powered data interpretation
- Entity extraction and validation
- Comprehensive profile assembly
- Confidence scoring

#### 4. Content Generation Layer
**Module**: `auto_enrich/ai_enrichment.py`  
**Documentation**: [docs/content-generation.md](docs/content-generation.md)
- Personalized email subjects
- Custom icebreakers
- Hot button identification
- A/B variant creation

## Campaign Context Configuration

Before enrichment, the system needs to understand your campaign objectives:

```python
campaign_context = {
    'campaign_goal': 'What are you trying to achieve?',
    'target_information': ['website', 'owner', 'contact', 'reviews'],
    'personalization_focus': 'recent_activity|pain_points|achievements',
    'industry_context': {
        'terms': ['industry-specific', 'keywords'],
        'services': ['what-they-offer'],
        'competitors': ['market-players']
    },
    'value_proposition': 'What you offer them',
    'tone': 'professional|casual|technical'
}
```

## Data Flow

### Input Requirements
- CSV with company identifying information
- Flexible column mapping via UI
- Campaign context and objectives

### Processing Stages
1. **Parse & Validate**: Column mapping, data cleaning
2. **Search & Gather**: Optimized queries, web scraping  
3. **Interpret & Build**: AI extraction, profile creation
4. **Generate & Personalize**: Content creation
5. **Export & Track**: Enriched CSV, job status

### Output Structure
```
Original Columns + 
- Website URL
- Owner Name (First, Last)
- Owner Contact (Phone, Email)
- LinkedIn Profile
- Email Subject Line
- Email Icebreaker
- Hot Button Topics
- Enrichment Confidence Score
```

## Web Interface

### Frontend Components
- **unified.html**: Main enrichment interface
- **mapper.html**: Column mapping tool
- **status.html**: Job monitoring
- **history.html**: Past enrichments

### API Endpoints
- `POST /api/upload`: CSV upload and analysis
- `POST /api/enrich`: Start enrichment job
- `GET /api/job/{id}`: Check job status
- `GET /api/download/{id}`: Download results

## Performance & Scaling

### Concurrency Control
```bash
# Default: 3 concurrent enrichments
python -m auto_enrich.enricher --concurrency 5

# Heavy load: Increase with caution
python -m auto_enrich.enricher --concurrency 10
```

### Resource Management
- Browser context pooling
- API rate limiting
- Memory optimization
- Error recovery

## Testing & Validation

### Test Individual Components
```bash
# Test search optimization
python test_selenium_direct.py

# Test known business
python test_known_dealer.py

# Test full pipeline
python test_single_enrichment.py
```

### Monitoring
```bash
# Real-time monitoring
python monitor.py

# Check logs
tail -f app.log
```

## Environment Configuration

### Required Variables
```env
LLM_API_KEY=your-openai-key
LLM_MODEL_NAME=gpt-4  # or gpt-3.5-turbo
```

### Optional Variables
```env
ENRICHMENT_CONCURRENCY=3
SEARCH_TIMEOUT=15
SCRAPE_TIMEOUT=30
ENABLE_CACHE=true
DEBUG_MODE=false
```

## Troubleshooting

### Common Issues
1. **100% Failure Rate**: Check search engine access, use Selenium mode
2. **No Owner Found**: Verify scraping patterns, check LinkedIn integration
3. **Generic Content**: Ensure campaign context is properly configured
4. **Slow Performance**: Adjust concurrency, check network latency

### Debug Mode
```bash
# Enable detailed logging
DEBUG_MODE=true python -m auto_enrich.enricher --input test.csv
```

## Documentation Index

### Core Documentation
- [Search Optimization](docs/search-optimization.md) - Query construction and search strategies
- [Data Collection](docs/data-collection.md) - Web scraping and information gathering
- [Profile Building](docs/profile-building.md) - AI interpretation and profile assembly
- [Content Generation](docs/content-generation.md) - Personalized content creation

### Technical Documentation
- [API Specifications](docs/API_SPECIFICATIONS.md) - REST API details
- [Database Schema](docs/DATABASE_SCHEMA.md) - Data model definitions
- [Implementation Guide](docs/IMPLEMENTATION_GUIDE.md) - Development guidelines

### Project Management
- [Product Backlog](docs/PRODUCT_BACKLOG_MVP.md) - Feature roadmap
- [Sprint Plan](docs/SPRINT_PLAN.md) - Development timeline
- [User Stories](docs/USER_STORIES_MVP.md) - Feature requirements

## Next Steps

1. **Immediate Priorities**
   - [ ] Implement campaign context collection UI
   - [ ] Add multi-source scraping (visit multiple search results)
   - [ ] Create profile persistence layer
   - [ ] Build quality scoring system

2. **Near-term Enhancements**
   - [ ] LinkedIn API integration
   - [ ] Email deliverability testing
   - [ ] A/B testing framework
   - [ ] Performance dashboard

3. **Long-term Vision**
   - [ ] Machine learning optimization
   - [ ] Multi-channel content (SMS, social)
   - [ ] CRM integrations
   - [ ] Predictive analytics

## Support & Contribution

For questions or contributions, refer to:
- Technical issues: Review logs and debug output
- Feature requests: Update PRODUCT_BACKLOG_MVP.md
- Documentation: Keep all docs current with implementation