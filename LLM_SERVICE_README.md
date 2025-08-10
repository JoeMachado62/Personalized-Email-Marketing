# Enhanced LLM Service and Content Generation System

## Overview

This enhanced LLM service provides a complete solution for generating personalized email content for automotive dealerships. It features multiple LLM provider support, advanced cost tracking, quality scoring, and industry-specific optimizations.

## 🌟 Key Features

- **Multi-Provider Support**: OpenAI and Anthropic with automatic fallback
- **Cost Optimization**: Intelligent batching and caching to stay under $0.02/record
- **Quality Scoring**: Automated content quality assessment and recommendations  
- **Industry-Specific Templates**: Tailored for car dealership marketing
- **Multiple Email Tones**: Professional, Friendly, and Urgent variations
- **Rate Limiting**: Built-in API rate limiting and retry logic
- **Caching System**: Smart caching to reduce costs and improve performance
- **Backward Compatibility**: Seamless integration with existing systems

## 📁 File Structure

```
app/
├── services/
│   ├── llm_service.py          # Core LLM abstraction with provider pattern
│   └── content_generator.py    # Advanced content generation orchestrator
├── prompts/
│   └── templates.py            # Industry-specific templates and prompts
└── config.py                   # Enhanced configuration settings

auto_enrich/
└── ai_enrichment.py            # Enhanced with new system integration

# Testing and Examples
test_llm_service.py             # Comprehensive test suite
integration_example.py          # Integration demonstration
LLM_SERVICE_README.md           # This documentation
```

## 🚀 Quick Start

### 1. Install Dependencies

The system uses existing dependencies. No additional packages required.

### 2. Configure API Keys

Add to your `.env` file:

```env
# Primary LLM Provider
LLM_API_KEY=your_openai_or_anthropic_key
LLM_PROVIDER=openai  # or "anthropic"
LLM_MODEL=gpt-4o-mini

# Optional: Multiple providers for fallback
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# Optional: Advanced configuration
LLM_CACHE_SIZE=1000
LLM_RATE_LIMIT_PER_MINUTE=50
MAX_COST_PER_RECORD=0.02
```

### 3. Basic Usage

```python
from app.services.content_generator import content_generator, ContentRequest
from app.prompts.templates import DealershipType, EmailTone

# Create a content request
request = ContentRequest(
    dealership_name="Miami Motors",
    city="Miami",
    website="https://miamimotors.com",
    owner_email="john@miamimotors.com",
    dealership_type=DealershipType.USED_CAR,
    tones=[EmailTone.PROFESSIONAL, EmailTone.FRIENDLY]
)

# Generate content
result = await content_generator.generate_content(request)

# Access generated variations
for variation in result.variations:
    print(f"{variation.tone.value}: {variation.subject}")
```

### 4. Backward Compatible Usage

```python
from auto_enrich.ai_enrichment import generate_email_content

# Original function still works, now enhanced
subject, icebreaker, hot_button = await generate_email_content(
    dealer_name="Miami Motors",
    city="Miami", 
    current_website="https://miamimotors.com",
    owner_email="john@miamimotors.com"
)
```

## 🎯 Content Generation Features

### Email Tone Variations

- **Professional**: Business-focused, ROI-driven, authoritative
- **Friendly**: Conversational, community-focused, supportive  
- **Urgent**: Time-sensitive, opportunity-focused, compelling

### Dealership Types

- **Used Car**: Focus on inventory turnover, trust building
- **New Car**: Manufacturer compliance, service profitability
- **Luxury**: Premium experience, high-net-worth customers
- **Commercial**: Fleet management, utility vehicles
- **Motorcycle**: Specialized for bike dealerships
- **RV/Boat**: Recreational vehicle focus

### Quality Scoring System

Each generated variation receives quality scores (0-100) for:
- **Subject Line**: Length, personalization, professionalism
- **Icebreaker**: Specificity, personalization, business focus
- **Hot Button**: Industry relevance, actionable language
- **Overall Score**: Weighted combination of all factors

## 💰 Cost Management

### Cost Optimization Features

1. **Intelligent Batching**: Generate multiple tones in single API call
2. **Smart Caching**: Cache similar prompts to reduce repeated calls
3. **Provider Selection**: Automatically choose most cost-effective provider
4. **Token Optimization**: Efficient prompt engineering to minimize tokens
5. **Budget Enforcement**: Automatic fallback when budget limits approached

### Cost Breakdown (Estimated)

| Provider | Model | Cost per 1K tokens | Estimated per record |
|----------|-------|-------------------|---------------------|
| OpenAI | gpt-4o-mini | $0.0001-$0.0006 | $0.005-$0.012 |
| OpenAI | gpt-4-turbo | $0.010-$0.030 | $0.050-$0.150 |
| Anthropic | Claude-3-Haiku | $0.00025-$0.00125 | $0.008-$0.015 |
| Anthropic | Claude-3-Sonnet | $0.003-$0.015 | $0.020-$0.080 |

## 📊 Performance Monitoring

### Built-in Metrics

```python
from app.services.llm_service import llm_service

metrics = llm_service.get_metrics()
print(f"Total API calls: {metrics.api_calls}")
print(f"Total cost: ${metrics.total_cost:.4f}")
print(f"Cache hit rate: {metrics.cache_hits / (metrics.cache_hits + metrics.cache_misses) * 100:.1f}%")
print(f"Average response time: {metrics.average_response_time:.2f}s")
```

### Quality Analytics

```python
quality_summary = content_generator.get_quality_summary(generated_content)
print(f"Overall quality: {quality_summary['overall_quality']:.1f}/100")
print(f"Best variation: {quality_summary['best_variation_tone']}")
print("Recommendations:", quality_summary['recommendations'])
```

## 🛠️ Advanced Usage

### Batch Processing

```python
requests = [
    ContentRequest(dealership_name="Dealer 1", city="City 1"),
    ContentRequest(dealership_name="Dealer 2", city="City 2"),
    ContentRequest(dealership_name="Dealer 3", city="City 3")
]

results = await content_generator.generate_batch(requests, max_concurrent=3)
```

### Custom Provider Configuration

```python
from app.services.llm_service import llm_service

# Generate with specific provider
response = await llm_service.generate(
    prompt="Generate email subject line",
    provider="anthropic",
    model="claude-3-haiku-20240307",
    temperature=0.8
)
```

### Enhanced Prompt Templates

```python
from app.prompts.templates import DealershipPrompts

# Build optimized multi-tone prompt
prompt = DealershipPrompts.build_optimized_prompt(
    dealership_name="Elite Motors",
    city="Beverly Hills",
    dealership_type=DealershipType.LUXURY,
    tones=[EmailTone.PROFESSIONAL, EmailTone.URGENT]
)
```

## 🔧 Configuration Options

### Environment Variables

```env
# Core Settings
LLM_API_KEY=your_key
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini

# Performance Tuning
LLM_CACHE_SIZE=1000              # Number of cached responses
LLM_CACHE_TTL_SECONDS=3600       # Cache expiration time
LLM_RATE_LIMIT_PER_MINUTE=50     # API rate limit
LLM_TIMEOUT_SECONDS=30           # Request timeout

# Content Generation
DEFAULT_MAX_TOKENS=400           # Default token limit
DEFAULT_TEMPERATURE=0.7          # Default creativity level
MAX_COST_PER_RECORD=0.02        # Budget per dealership
QUALITY_THRESHOLD=70.0          # Minimum quality score
```

### Runtime Configuration

```python
from app.config import settings

# Modify settings at runtime
settings.MAX_COST_PER_RECORD = 0.015
settings.QUALITY_THRESHOLD = 80.0
```

## 🧪 Testing

### Run Comprehensive Tests

```bash
python test_llm_service.py
```

### Run Integration Example

```bash
python integration_example.py
```

### Test Coverage

- Basic LLM service functionality
- Content generation with multiple tones
- Batch processing performance
- Quality scoring accuracy
- Cost optimization effectiveness
- Error handling and fallbacks
- Cache performance
- Backward compatibility

## 🔍 Error Handling

### Built-in Fallback Strategies

1. **Provider Fallback**: Automatically switch providers on failure
2. **Template Fallback**: Use pre-built templates if API fails
3. **Graceful Degradation**: Return partial results when possible
4. **Error Logging**: Comprehensive error tracking and metrics

### Example Error Handling

```python
try:
    result = await content_generator.generate_content(request)
    if result.variations:
        # Process successful results
        process_variations(result.variations)
    else:
        # Handle empty results
        use_fallback_content()
except Exception as e:
    # Log error and use fallback
    logger.error(f"Content generation failed: {e}")
    use_template_content()
```

## 📈 Performance Optimization Tips

### 1. Cost Optimization
- Use `gpt-4o-mini` for most tasks (lowest cost)
- Enable caching for similar dealerships
- Use batch processing for multiple records
- Set appropriate budget limits

### 2. Quality Optimization  
- Provide detailed context in `extra_context`
- Use specific dealership types
- Include website information when available
- Review and improve low-scoring content

### 3. Speed Optimization
- Use appropriate `max_concurrent` limits
- Enable caching with reasonable TTL
- Choose fastest models when quality permits
- Pre-warm cache with common patterns

## 🚨 Common Issues and Solutions

### Issue: High Costs
**Solution**: 
- Check `MAX_COST_PER_RECORD` setting
- Enable caching
- Use batch generation
- Switch to lower-cost models

### Issue: Low Quality Scores
**Solution**:
- Provide more specific context
- Use appropriate dealership types
- Include owner names and website info
- Adjust quality thresholds

### Issue: API Rate Limits
**Solution**:
- Reduce `LLM_RATE_LIMIT_PER_MINUTE`
- Increase `max_concurrent` delays
- Use multiple providers for load distribution

### Issue: Timeouts
**Solution**:
- Increase `LLM_TIMEOUT_SECONDS`
- Reduce `max_tokens` per request
- Check network connectivity

## 🔄 Migration Guide

### From Original System

The enhanced system is fully backward compatible:

```python
# Old way (still works)
from auto_enrich.ai_enrichment import generate_email_content
subject, icebreaker, hot_button = await generate_email_content(...)

# New way (enhanced features)
from auto_enrich.ai_enrichment import generate_enhanced_email_content
result = await generate_enhanced_email_content(...)
```

### Integration Checklist

- [ ] Configure API keys in `.env`
- [ ] Test with small batch first
- [ ] Monitor costs and quality
- [ ] Adjust configuration as needed
- [ ] Update existing workflows gradually

## 📝 Example Outputs

### Professional Tone
- **Subject**: "John: Strategic Growth for Miami Motors"
- **Icebreaker**: "I've been analyzing successful dealerships in Miami, and Miami Motors' focus on customer satisfaction and competitive pricing positions you well for the current market conditions."
- **Hot Button**: "Many used car dealers in your area are seeing 20-30% improvements in qualified lead generation with the right digital marketing strategy."

### Friendly Tone  
- **Subject**: "Hi John - Growing Miami Motors Together"
- **Icebreaker**: "Hi John, I hope you're having a great week at Miami Motors! I've been working with several used car dealers in Miami and thought you might be interested in some trends I'm seeing in the local market."
- **Hot Button**: "Most dealers I work with tell me that converting online inquiries into showroom visits is their biggest challenge right now."

### Urgent Tone
- **Subject**: "John: Miami Market Opportunity for Miami Motors"  
- **Icebreaker**: "The Miami automotive market is shifting rapidly, and forward-thinking dealers like Miami Motors have a unique window of opportunity right now to capture market share."
- **Hot Button**: "Dealers who don't optimize their online presence in the next 90 days typically see a 15-25% drop in qualified leads."

## 📚 Additional Resources

- **API Documentation**: Check provider docs for OpenAI/Anthropic
- **Best Practices**: See `integration_example.py` for patterns
- **Performance Tuning**: Use `test_llm_service.py` for benchmarking
- **Industry Templates**: Extend `app/prompts/templates.py`

## 🤝 Support and Maintenance

### Regular Maintenance Tasks

1. **Monitor Costs**: Review monthly spend and adjust limits
2. **Quality Review**: Check scores and update templates
3. **Performance Monitoring**: Track response times and cache hit rates  
4. **Error Analysis**: Review error logs and improve fallbacks
5. **Template Updates**: Refresh templates based on performance data

### Support

For issues or questions:
1. Check error logs and metrics
2. Review configuration settings
3. Test with `test_llm_service.py`
4. Check API provider status
5. Review cost and rate limits

---

**Built for automotive dealership marketing excellence** 🚗✨