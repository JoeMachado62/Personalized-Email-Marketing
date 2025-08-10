# Profile Building & Data Interpretation

## Overview
This document outlines how raw scraped data is transformed into comprehensive business profiles using AI interpretation and structured extraction.

## Profile Building Pipeline

### DataInterpreter (`auto_enrich/data_interpreter.py`)
Core component that uses AI to:
- Extract structured information from unstructured data
- Identify key business attributes
- Generate personalized content
- Build comprehensive profiles

## Profile Components

### 1. Business Identity
```python
profile = {
    'company_name': 'Official business name',
    'dba_names': ['Alternative names'],
    'entity_type': 'LLC/Corp/Inc',
    'established': 'Year founded',
    'industry': 'Primary industry classification'
}
```

### 2. Contact Information
```python
contact = {
    'primary_phone': 'Main business line',
    'alternate_phones': ['Secondary numbers'],
    'primary_email': 'Main contact email',
    'department_emails': {
        'sales': 'sales@example.com',
        'support': 'support@example.com'
    },
    'physical_address': 'Street address',
    'mailing_address': 'PO Box if different'
}
```

### 3. Decision Makers
```python
leadership = {
    'owner': {
        'first_name': 'John',
        'last_name': 'Doe',
        'title': 'Owner/President',
        'email': 'john@example.com',
        'phone': '(555) 123-4567',
        'linkedin': 'linkedin.com/in/johndoe'
    },
    'key_personnel': [
        {
            'name': 'Jane Smith',
            'role': 'General Manager',
            'department': 'Operations'
        }
    ]
}
```

### 4. Business Characteristics
```python
characteristics = {
    'size': 'Small/Medium/Large',
    'employee_count': 'Estimated range',
    'annual_revenue': 'Estimated range',
    'service_area': 'Geographic coverage',
    'specialties': ['Key services/products'],
    'certifications': ['Industry certifications'],
    'awards': ['Recognition received']
}
```

### 5. Digital Presence
```python
digital = {
    'website': 'Primary URL',
    'social_media': {
        'facebook': 'Profile URL',
        'linkedin': 'Company page',
        'instagram': 'Handle',
        'youtube': 'Channel'
    },
    'online_reputation': {
        'google_rating': 4.5,
        'review_count': 127,
        'sentiment': 'Positive/Neutral/Negative'
    }
}
```

### 6. Behavioral Insights
```python
insights = {
    'communication_style': 'Formal/Casual/Technical',
    'brand_voice': 'Professional/Friendly/Authoritative',
    'value_proposition': 'Key selling points',
    'pain_points': ['Identified challenges'],
    'opportunities': ['Potential needs']
}
```

## AI Interpretation Process

### Batch Extraction Strategy
Instead of multiple API calls, use single comprehensive prompt:

```python
async def _batch_extract_with_ai(self, scraped_data: Dict) -> Dict:
    prompt = """
    Analyze this business data and extract:
    1. Owner/decision maker information
    2. Contact details (phone, email)
    3. Business characteristics
    4. Key services/specialties
    5. Pain points and opportunities
    
    Data: {scraped_data}
    
    Return structured JSON with all findings.
    """
```

### Extraction Confidence Levels

#### High Confidence
- Data explicitly stated on website
- Consistent across multiple sources
- From official business profiles

#### Medium Confidence
- Inferred from context
- Single source mention
- Pattern-matched data

#### Low Confidence
- Assumption based on industry
- Outdated information
- Conflicting sources

## Profile Enrichment Strategies

### 1. Cross-Reference Validation
- Compare website data with GMB
- Verify social media consistency
- Check directory listings

### 2. Industry Intelligence
```python
industry_enrichment = {
    'market_position': 'Leader/Challenger/Niche',
    'competitive_landscape': ['Main competitors'],
    'industry_trends': ['Relevant trends'],
    'regulatory_environment': ['Key regulations']
}
```

### 3. Relationship Mapping
```python
relationships = {
    'parent_company': 'If subsidiary',
    'affiliations': ['Partner organizations'],
    'vendors': ['Known suppliers'],
    'clients': ['Notable customers']
}
```

## Profile Quality Metrics

### Completeness Score
- 90-100%: All critical fields populated
- 70-89%: Most fields complete
- 50-69%: Basic information available
- <50%: Insufficient data

### Data Freshness
- Current: Updated within 30 days
- Recent: Updated within 90 days
- Stale: Over 90 days old
- Unknown: No timestamp available

## Profile Storage Format

### JSON Structure
```json
{
  "profile_id": "unique_identifier",
  "created_at": "2024-01-15T10:00:00Z",
  "last_updated": "2024-01-15T10:00:00Z",
  "confidence_score": 0.85,
  "completeness_score": 0.92,
  "business_profile": {...},
  "contact_profile": {...},
  "leadership_profile": {...},
  "digital_profile": {...},
  "enrichment_metadata": {
    "sources_used": ["website", "gmb", "social"],
    "ai_model": "gpt-4",
    "extraction_time_ms": 2500
  }
}
```

## Use Cases

### 1. Sales Outreach
- Identify decision makers
- Understand pain points
- Personalize messaging

### 2. Market Research
- Competitive analysis
- Industry mapping
- Trend identification

### 3. Lead Scoring
- Evaluate fit
- Prioritize outreach
- Segment lists

### 4. Relationship Management
- Track changes over time
- Monitor digital presence
- Update contact information

## Best Practices

1. **Regular Updates**: Re-profile quarterly or on trigger events
2. **Source Attribution**: Always track where data originated
3. **Privacy Compliance**: Respect opt-outs and privacy laws
4. **Data Hygiene**: Regular validation and cleanup
5. **Feedback Loop**: Use outcome data to improve extraction

## Future Enhancements

1. **Predictive Analytics**
   - Buying propensity scores
   - Churn risk indicators
   - Growth trajectory prediction

2. **Behavioral Tracking**
   - Website engagement
   - Email interaction
   - Social media activity

3. **Integration Capabilities**
   - CRM synchronization
   - Marketing automation
   - Sales intelligence platforms

4. **Advanced AI Features**
   - Sentiment analysis
   - Intent detection
   - Personality profiling