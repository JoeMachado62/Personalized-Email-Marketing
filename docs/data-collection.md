# Data Collection & Web Scraping

## Overview
This document describes the multi-source data collection system that gathers comprehensive business information from various web sources.

## Data Collection Architecture

### WebDataGatherer (`auto_enrich/web_scraper.py`)
Primary class responsible for orchestrating data collection:
- Search engine queries
- Website scraping
- Business directory extraction
- Social media discovery

## Collection Strategy

### Phase 1: Search & Discovery
1. **Execute optimized search queries** (see search-optimization.md)
2. **Identify official website** from search results
3. **Detect Google My Business** panels
4. **Extract search snippets** for quick insights

### Phase 2: Website Scraping
Targeted extraction from identified websites:

#### Contact Information
- Phone numbers: `(?:\+?1[-.\\s]?)?\(?\d{3}\)?[-.\\s]?\d{3}[-.\\s]?\d{4}`
- Email addresses: `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b`
- Physical addresses: Street patterns with zip codes

#### Business Details
- Title and meta descriptions
- About Us content
- Team/staff information
- Service offerings
- Business hours

#### Ownership Information
Pattern matching for titles:
- Owner, President, CEO, Founder
- Management team listings
- LinkedIn profile references

### Phase 3: Multi-Source Aggregation

#### Google My Business
```python
gmb_data = {
    'business_name': 'Company Name',
    'address': 'Full Address',
    'phone': '(555) 123-4567',
    'website': 'https://example.com',
    'hours': 'Mon-Fri 9AM-5PM',
    'rating': 4.5,
    'review_count': 127
}
```

#### Social Media Profiles
- Facebook business pages
- LinkedIn company profiles
- Instagram business accounts
- Twitter/X profiles

#### Review Platforms
- Google Reviews
- Yelp
- Industry-specific platforms

## Data Structure

### Raw Scraped Data Format
```python
gathered_data = {
    'company_name': str,
    'location': str,
    'search_results': [
        {
            'title': str,
            'url': str,
            'snippet': str,
            'source': str
        }
    ],
    'website_data': {
        'url': str,
        'title': str,
        'meta_description': str,
        'contact_info': {
            'phones': [],
            'emails': [],
            'addresses': []
        },
        'about_text': [],
        'key_phrases': []
    },
    'social_profiles': {
        'facebook': str,
        'linkedin': str,
        'instagram': str
    },
    'business_info': {
        'hours': str,
        'services': [],
        'specialties': []
    }
}
```

## Technical Implementation

### Playwright Configuration
```python
browser = await playwright.chromium.launch(
    headless=True,
    args=['--disable-blink-features=AutomationControlled']
)
context = await browser.new_context(
    viewport={'width': 1920, 'height': 1080},
    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
)
```

### Selenium Alternative
For sites with aggressive bot detection:
```python
from selenium import webdriver
options = webdriver.ChromeOptions()
options.add_argument("--disable-blink-features=AutomationControlled")
driver = webdriver.Chrome(options=options)
```

## Error Handling

### Retry Logic
- Max retries: 2 per URL
- Timeout: 15 seconds per page
- Backoff: 2 seconds between retries

### Fallback Strategies
1. If website scraping fails → Use search snippets
2. If primary URL fails → Try alternate URLs from search
3. If all scraping fails → Use cached/partial data

## Performance Optimization

### Concurrent Processing
- Semaphore-limited concurrent scraping
- Default: 3 concurrent operations
- Adjustable via `--concurrency` parameter

### Caching Strategy
- Cache search results for 15 minutes
- Store successful scrapes for session
- Reuse browser contexts when possible

## Data Quality Measures

### Validation Rules
1. **Phone numbers**: Must match standard formats
2. **Emails**: Must have valid domain
3. **URLs**: Must be accessible (200 OK)
4. **Addresses**: Must include city/state or zip

### Confidence Scoring
- High: Data from official website + GMB
- Medium: Data from search results + social
- Low: Only search snippets available

## Privacy & Compliance

### Respect robots.txt
- Check before scraping
- Honor crawl delays
- Respect disallow directives

### Rate Limiting
- 1-2 second delays between requests
- Randomized user agents
- Session rotation

## Future Enhancements

1. **API Integration**
   - Google Places API
   - Facebook Graph API
   - LinkedIn API

2. **Advanced Extraction**
   - Computer vision for logos/images
   - PDF document parsing
   - Video content analysis

3. **Data Enrichment Sources**
   - Government databases
   - Industry directories
   - News aggregators

4. **Machine Learning**
   - Entity recognition
   - Relationship extraction
   - Data validation models