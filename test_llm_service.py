"""
Test script for the LLM service and content generation system.

This script demonstrates the complete functionality of the enhanced LLM service
including multiple providers, cost tracking, quality scoring, and batch generation.
"""

import asyncio
import os
import json
from typing import List

# Add app directory to Python path
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from app.services.llm_service import llm_service
from app.services.content_generator import content_generator, ContentRequest
from app.prompts.templates import DealershipType, EmailTone, QualityScorer
from auto_enrich.ai_enrichment import generate_enhanced_email_content


async def test_basic_llm_service():
    """Test basic LLM service functionality."""
    print("=== Testing Basic LLM Service ===")
    
    try:
        # Test simple generation
        prompt = "Write a professional email subject line for a car dealership owner named John in Miami."
        response = await llm_service.generate(prompt, max_tokens=50)
        
        print(f"Generated content: {response.content}")
        print(f"Tokens used: {response.tokens_used}")
        print(f"Cost: ${response.cost:.4f}")
        print(f"Provider: {response.provider}")
        print(f"Cached: {response.cached}")
        
        # Test caching
        print("\n--- Testing Cache ---")
        cached_response = await llm_service.generate(prompt, max_tokens=50)
        print(f"Second call cached: {cached_response.cached}")
        print(f"Second call cost: ${cached_response.cost:.4f}")
        
    except Exception as e:
        print(f"Error testing basic LLM service: {e}")


async def test_content_generator():
    """Test advanced content generation."""
    print("\n=== Testing Content Generator ===")
    
    try:
        # Test single dealership
        request = ContentRequest(
            dealership_name="Miami Motors",
            city="Miami",
            website="https://miamimotors.com",
            owner_email="john.smith@miamimotors.com",
            dealership_type=DealershipType.USED_CAR,
            extra_context="Family-owned dealership, 15 years in business, specializes in affordable vehicles",
            tones=[EmailTone.PROFESSIONAL, EmailTone.FRIENDLY],
            max_cost_per_record=0.02
        )
        
        generated_content = await content_generator.generate_content(request)
        
        print(f"Dealership: {generated_content.dealership_name}")
        print(f"Owner name derived: {generated_content.owner_name}")
        print(f"Total cost: ${generated_content.total_cost:.4f}")
        print(f"Total tokens: {generated_content.total_tokens}")
        print(f"Generation time: {generated_content.generation_time:.2f}s")
        
        print("\nGenerated Variations:")
        for i, variation in enumerate(generated_content.variations):
            print(f"\n--- Variation {i+1}: {variation.tone.value.title()} ---")
            print(f"Subject: {variation.subject}")
            print(f"Icebreaker: {variation.icebreaker}")
            print(f"Hot Button: {variation.hot_button}")
            print(f"Overall Quality Score: {variation.quality_scores.get('overall_score', 0):.1f}/100")
            print(f"Cost: ${variation.cost:.4f}")
            print(f"Tokens: {variation.tokens_used}")
        
        # Get quality summary
        quality_summary = content_generator.get_quality_summary(generated_content)
        print(f"\nQuality Summary:")
        print(f"Overall Quality: {quality_summary['overall_quality']:.1f}/100")
        print(f"Best Variation: {quality_summary['best_variation_tone']}")
        print("Recommendations:")
        for rec in quality_summary['recommendations']:
            print(f"  - {rec}")
            
    except Exception as e:
        print(f"Error testing content generator: {e}")


async def test_batch_generation():
    """Test batch content generation."""
    print("\n=== Testing Batch Generation ===")
    
    try:
        # Create multiple requests
        requests = [
            ContentRequest(
                dealership_name="Sunshine Auto Sales",
                city="Orlando",
                owner_email="mike.johnson@sunshineauto.com",
                dealership_type=DealershipType.USED_CAR,
                tones=[EmailTone.PROFESSIONAL]
            ),
            ContentRequest(
                dealership_name="Elite Motors",
                city="Tampa",
                owner_email="sarah.davis@elitemotors.com",
                dealership_type=DealershipType.LUXURY,
                tones=[EmailTone.PROFESSIONAL]
            ),
            ContentRequest(
                dealership_name="Downtown Honda",
                city="Jacksonville",
                owner_email="info@downtownhonda.com",
                dealership_type=DealershipType.NEW_CAR,
                tones=[EmailTone.FRIENDLY]
            )
        ]
        
        # Generate batch
        start_time = asyncio.get_event_loop().time()
        results = await content_generator.generate_batch(requests, max_concurrent=2)
        end_time = asyncio.get_event_loop().time()
        
        print(f"Generated content for {len(results)} dealerships in {end_time - start_time:.2f} seconds")
        
        total_cost = sum(result.total_cost for result in results)
        total_tokens = sum(result.total_tokens for result in results)
        
        print(f"Total cost: ${total_cost:.4f}")
        print(f"Total tokens: {total_tokens}")
        print(f"Average cost per dealership: ${total_cost/len(results):.4f}")
        
        # Show sample results
        for i, result in enumerate(results):
            print(f"\n--- Dealership {i+1}: {result.dealership_name} ---")
            if result.variations:
                variation = result.variations[0]
                print(f"Subject: {variation.subject}")
                print(f"Quality Score: {variation.quality_scores.get('overall_score', 0):.1f}/100")
                
    except Exception as e:
        print(f"Error testing batch generation: {e}")


async def test_enhanced_ai_enrichment():
    """Test the enhanced AI enrichment module."""
    print("\n=== Testing Enhanced AI Enrichment Module ===")
    
    try:
        # Test backward compatibility
        from auto_enrich.ai_enrichment import generate_email_content
        
        print("Testing backward compatible function...")
        subject, icebreaker, hot_button = await generate_email_content(
            dealer_name="Classic Cars of Atlanta",
            city="Atlanta",
            current_website="https://classicatl.com",
            owner_email="robert.wilson@classicatl.com",
            extra_context="Specializes in classic and vintage automobiles"
        )
        
        print(f"Subject: {subject}")
        print(f"Icebreaker: {icebreaker}")
        print(f"Hot Button: {hot_button}")
        
        # Test enhanced function
        print("\nTesting enhanced function...")
        enhanced_result = await generate_enhanced_email_content(
            dealer_name="Modern Motors",
            city="Houston",
            current_website="https://modernmotors.com",
            owner_email="lisa.garcia@modernmotors.com",
            dealership_type="luxury",
            extra_context="Luxury dealer specializing in European imports",
            tones=["professional", "friendly"]
        )
        
        print(f"Enhanced result cost: ${enhanced_result['total_cost']:.4f}")
        print(f"Overall quality: {enhanced_result['quality_summary']['overall_quality']:.1f}")
        
        for variation in enhanced_result['variations']:
            print(f"\n{variation['tone'].title()} Tone:")
            print(f"  Subject: {variation['subject']}")
            print(f"  Quality: {variation['quality_scores']['overall_score']:.1f}/100")
            
    except Exception as e:
        print(f"Error testing enhanced AI enrichment: {e}")


async def test_quality_scoring():
    """Test the quality scoring system."""
    print("\n=== Testing Quality Scoring System ===")
    
    scorer = QualityScorer()
    
    # Test different subject lines
    subjects = [
        ("John: Boost Miami Motors Sales Today", "John"),
        ("FREE CARS!!! ACT NOW!!!", None),
        ("Strategic Growth Opportunity", None),
        ("Mike: Your Tampa Dealership's Future", "Mike"),
    ]
    
    print("Subject Line Quality Scores:")
    for subject, owner in subjects:
        score = scorer.score_subject_line(subject, owner)
        print(f"  '{subject}' -> {score:.1f}/100")
    
    # Test icebreaker scoring
    icebreakers = [
        "I hope this email finds you well. I wanted to reach out about marketing.",
        "I noticed Miami Motors has been serving the South Florida community for over a decade. Your focus on affordable, reliable vehicles really stands out in the competitive Miami market.",
        "Hi there! Great dealership you have!",
        "After researching successful dealerships in Tampa, Elite Motors' commitment to luxury service and premium inventory positioning caught my attention."
    ]
    
    print("\nIcebreaker Quality Scores:")
    for icebreaker in icebreakers:
        score = scorer.score_icebreaker(icebreaker, "Miami Motors", "Miami")
        print(f"  Score: {score:.1f}/100")
        print(f"  Text: {icebreaker[:60]}{'...' if len(icebreaker) > 60 else ''}")
        print()


async def test_cost_optimization():
    """Test cost optimization features."""
    print("\n=== Testing Cost Optimization ===")
    
    # Test cost estimation
    sample_request = ContentRequest(
        dealership_name="Test Motors",
        city="Test City",
        tones=[EmailTone.PROFESSIONAL, EmailTone.FRIENDLY, EmailTone.URGENT]
    )
    
    estimated_cost = await content_generator._estimate_generation_cost(
        sample_request, 
        [EmailTone.PROFESSIONAL, EmailTone.FRIENDLY, EmailTone.URGENT]
    )
    
    print(f"Estimated cost for 3 variations: ${estimated_cost:.4f}")
    
    # Test with cost limit
    budget_request = ContentRequest(
        dealership_name="Budget Motors",
        city="Budget City",
        tones=[EmailTone.PROFESSIONAL, EmailTone.FRIENDLY, EmailTone.URGENT],
        max_cost_per_record=0.005  # Very low budget
    )
    
    try:
        result = await content_generator.generate_content(budget_request)
        print(f"Actual cost with budget limit: ${result.total_cost:.4f}")
        print(f"Number of variations generated: {len(result.variations)}")
    except Exception as e:
        print(f"Budget constraint handling: {e}")


async def show_metrics():
    """Display service metrics."""
    print("\n=== Service Metrics ===")
    
    metrics = llm_service.get_metrics()
    
    print(f"Total API calls: {metrics.api_calls}")
    print(f"Total tokens used: {metrics.total_tokens}")
    print(f"Total cost: ${metrics.total_cost:.4f}")
    print(f"Cache hit rate: {metrics.cache_hits / (metrics.cache_hits + metrics.cache_misses) * 100 if (metrics.cache_hits + metrics.cache_misses) > 0 else 0:.1f}%")
    print(f"Average response time: {metrics.average_response_time:.2f}s")


async def main():
    """Run all tests."""
    print("🚀 Testing LLM Service and Content Generation System")
    print("=" * 60)
    
    # Check if API key is configured
    from app.config import settings
    if not settings.LLM_API_KEY:
        print("⚠️  Warning: LLM_API_KEY not configured. Tests will use fallback templates.")
        print("Set LLM_API_KEY in your environment or .env file for full functionality.")
        print()
    
    # Run tests
    await test_basic_llm_service()
    await test_content_generator()
    await test_batch_generation()
    await test_enhanced_ai_enrichment()
    await test_quality_scoring()
    await test_cost_optimization()
    await show_metrics()
    
    print("\n✅ All tests completed!")
    print("\nNext steps:")
    print("1. Configure your LLM API keys in the .env file")
    print("2. Integrate the content generator into your workflow")
    print("3. Monitor costs and quality metrics")
    print("4. Adjust prompts and templates as needed")


if __name__ == "__main__":
    asyncio.run(main())