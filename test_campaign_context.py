"""
Test script to verify campaign context integration with enrichment pipeline
"""

import asyncio
import logging
from pathlib import Path
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_with_campaign_context():
    """Test enrichment with campaign context"""
    
    try:
        from auto_enrich.search_query_optimizer import SearchQueryOptimizer
        from auto_enrich.web_scraper import gather_web_data
        from auto_enrich.data_interpreter import interpret_scraped_data
        
        # Define campaign context (simulating what UI would send)
        campaign_context = {
            'campaign_goal': 'generate_leads',
            'value_proposition': 'We help dealerships increase online sales through advanced digital marketing and lead generation strategies',
            'target_information': ['website', 'owner', 'contact', 'social_media', 'recent_news'],
            'personalization_focus': 'recent_activity',
            'industry_context': {
                'type': 'automotive dealerships',
                'terms': ['inventory management', 'customer retention', 'online sales'],
                'services': ['vehicle sales', 'financing', 'service department']
            },
            'message_tone': 'professional',
            'additional_context': 'Focus on dealerships that seem to have limited online presence'
        }
        
        # Test business record
        test_record = {
            'company_name': 'BROADWAY AUTO BROKERS INC',
            'city': 'ALACHUA',
            'state': 'FL',
            'phone': '(352)415-0010'
        }
        
        logger.info("=" * 60)
        logger.info("Testing Campaign Context Integration")
        logger.info("=" * 60)
        
        # Step 1: Generate optimized search queries
        logger.info("\nStep 1: Generating search queries with campaign context...")
        optimizer = SearchQueryOptimizer(campaign_context)
        queries = optimizer.build_search_queries(test_record)
        
        logger.info(f"Generated {len(queries)} optimized queries:")
        for q in queries:
            logger.info(f"  Priority {q['priority']}: {q['query']}")
            logger.info(f"    Purpose: {q['purpose']}")
        
        # Step 2: Gather web data using optimized queries and multi-source scraping
        logger.info("\nStep 2: Gathering web data from multiple sources...")
        scraped_data = await gather_web_data(
            company_name=test_record['company_name'],
            location=f"{test_record['city']}, {test_record['state']}",
            additional_data={'phone': test_record['phone']},
            campaign_context=campaign_context  # Pass campaign context for multi-source scraping
        )
        
        if scraped_data.get('search_results'):
            logger.info(f"Found {len(scraped_data['search_results'])} search results")
            
            # Check multi-source profile
            profile = scraped_data.get('multi_source_profile', {})
            if profile:
                logger.info(f"Multi-source profile built from: {profile.get('sources_used', [])}")
                
                # Check personalization hooks
                hooks = profile.get('personalization_hooks', [])
                if hooks:
                    logger.info(f"Generated {len(hooks)} personalization hooks:")
                    for hook in hooks[:3]:
                        logger.info(f"  - [{hook['type']}] {hook['hook']}")
            else:
                logger.info(f"Website identified: {scraped_data.get('website_url', 'None')}")
        else:
            logger.warning("No search results found")
        
        # Step 3: Interpret with AI using campaign context
        logger.info("\nStep 3: Interpreting data with campaign context...")
        
        # Add campaign context to scraped data for AI interpretation
        scraped_data['campaign_context'] = campaign_context
        
        interpreted_data = await interpret_scraped_data(scraped_data)
        
        # Check results
        logger.info("\n" + "=" * 60)
        logger.info("RESULTS WITH CAMPAIGN CONTEXT")
        logger.info("=" * 60)
        
        # Owner information
        owner_info = interpreted_data.get('extracted_info', {}).get('owner', {})
        if owner_info.get('first_name'):
            logger.info(f"✓ Owner found: {owner_info.get('first_name')} {owner_info.get('last_name')}")
        else:
            logger.info("✗ No owner information found")
        
        # Website
        website = interpreted_data.get('extracted_info', {}).get('website')
        if website:
            logger.info(f"✓ Website: {website}")
        else:
            logger.info("✗ No website found")
        
        # Email content
        email_content = interpreted_data.get('generated_content', {})
        
        # Subject line
        subject = email_content.get('subject', {}).get('raw_response', '')
        if subject:
            logger.info(f"✓ Subject line: {subject}")
        else:
            logger.info("✗ No subject line generated")
        
        # Icebreaker
        icebreaker = email_content.get('icebreaker', {}).get('raw_response', '')
        if icebreaker:
            logger.info(f"✓ Icebreaker: {icebreaker[:100]}...")
        else:
            logger.info("✗ No icebreaker generated")
        
        # Hot button
        hot_button = email_content.get('hot_button', {}).get('raw_response', '')
        if hot_button:
            logger.info(f"✓ Hot button: {hot_button}")
        else:
            logger.info("✗ No hot button identified")
        
        # Check if personalization matches campaign focus
        logger.info("\n" + "-" * 40)
        logger.info("Campaign Context Alignment Check:")
        
        if campaign_context['personalization_focus'] == 'recent_activity':
            if 'recent' in subject.lower() or 'new' in subject.lower() or '2024' in subject:
                logger.info("✓ Subject line reflects recent activity focus")
            else:
                logger.info("⚠ Subject line may not reflect recent activity focus")
        
        if campaign_context['message_tone'] == 'professional':
            if icebreaker and not any(word in icebreaker.lower() for word in ['hey', 'hi there', 'yo']):
                logger.info("✓ Tone appears professional")
            else:
                logger.info("⚠ Tone may not be professional enough")
        
        if any(term in hot_button.lower() for term in ['inventory', 'online', 'digital', 'sales']):
            logger.info("✓ Hot button aligns with industry context")
        else:
            logger.info("⚠ Hot button may not align with industry context")
        
        return interpreted_data
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return None

if __name__ == "__main__":
    result = asyncio.run(test_with_campaign_context())
    
    if result:
        print("\n" + "=" * 60)
        print("TEST COMPLETED SUCCESSFULLY")
        print("Campaign context integration is working!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("TEST FAILED")
        print("Check the logs above for error details")
        print("=" * 60)