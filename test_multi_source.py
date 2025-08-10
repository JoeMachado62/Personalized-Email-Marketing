"""
Test multi-source scraping with profile building
"""

import asyncio
import logging
from pathlib import Path
import sys
import json

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_multi_source_scraping():
    """Test multi-source scraping with profile building"""
    
    try:
        from auto_enrich.web_scraper import gather_web_data
        from auto_enrich.data_interpreter import interpret_scraped_data
        
        # Define campaign context for targeted scraping
        campaign_context = {
            'campaign_goal': 'generate_leads',
            'value_proposition': 'We help businesses increase online visibility and customer engagement',
            'target_information': ['website', 'owner', 'contact', 'social_media', 'reviews', 'recent_news'],
            'personalization_focus': 'recent_activity',  # Focus on recent news/updates
            'message_tone': 'professional'
        }
        
        # Test with a well-known business that should have multiple sources
        test_company = "Starbucks"
        test_location = "Seattle, WA"
        
        logger.info("=" * 60)
        logger.info("TESTING MULTI-SOURCE SCRAPING")
        logger.info("=" * 60)
        logger.info(f"Company: {test_company}")
        logger.info(f"Location: {test_location}")
        logger.info(f"Campaign Focus: {campaign_context['personalization_focus']}")
        
        # Gather data from multiple sources
        logger.info("\nGathering data from multiple sources...")
        scraped_data = await gather_web_data(
            company_name=test_company,
            location=test_location,
            campaign_context=campaign_context
        )
        
        # Check search results
        logger.info(f"\nSearch results found: {len(scraped_data.get('search_results', []))}")
        
        # Check multi-source profile
        profile = scraped_data.get('multi_source_profile', {})
        if profile:
            logger.info("\n" + "=" * 40)
            logger.info("MULTI-SOURCE PROFILE RESULTS")
            logger.info("=" * 40)
            
            # Sources used
            sources = profile.get('sources_used', [])
            logger.info(f"\nSources scraped: {len(sources)}")
            for source in sources:
                logger.info(f"  ✓ {source}")
            
            # Owner information
            owner_info = profile.get('owner_info', {})
            if owner_info:
                logger.info(f"\nOwner/Leadership Info:")
                for key, value in owner_info.items():
                    logger.info(f"  {key}: {value}")
            
            # Recent activity
            recent = profile.get('recent_activity', [])
            if recent:
                logger.info(f"\nRecent Activity: {len(recent)} items found")
                for item in recent[:3]:
                    if isinstance(item, dict):
                        logger.info(f"  - {item.get('headline', item.get('text', str(item)[:100]))}")
            
            # Pain points from reviews
            pain_points = profile.get('pain_points', [])
            if pain_points:
                logger.info(f"\nPain Points Identified: {', '.join(set(pain_points))}")
            
            # Social presence
            social = profile.get('social_presence', {})
            if social:
                logger.info(f"\nSocial Media Presence:")
                for platform, url in social.items():
                    logger.info(f"  {platform}: {url[:50]}...")
            
            # Reputation
            reputation = profile.get('reputation', {})
            if reputation:
                logger.info(f"\nReputation Data:")
                if reputation.get('rating'):
                    logger.info(f"  Rating: {reputation['rating']} stars")
                if reputation.get('review_count'):
                    logger.info(f"  Reviews: {reputation['review_count']}")
            
            # Personalization hooks
            hooks = profile.get('personalization_hooks', [])
            if hooks:
                logger.info(f"\n🎯 PERSONALIZATION HOOKS GENERATED: {len(hooks)}")
                for i, hook in enumerate(hooks[:5], 1):
                    logger.info(f"  {i}. [{hook['type']}] {hook['hook']}")
                    logger.info(f"     Confidence: {hook['confidence']}")
        else:
            logger.warning("No multi-source profile generated")
        
        # Test another company with likely social media presence
        logger.info("\n" + "=" * 60)
        logger.info("TESTING WITH LOCAL BUSINESS")
        logger.info("=" * 60)
        
        test_company2 = "Joe's Pizza"
        test_location2 = "New York, NY"
        
        logger.info(f"Company: {test_company2}")
        logger.info(f"Location: {test_location2}")
        
        scraped_data2 = await gather_web_data(
            company_name=test_company2,
            location=test_location2,
            campaign_context={
                **campaign_context,
                'personalization_focus': 'pain_points'  # Focus on reviews for this one
            }
        )
        
        profile2 = scraped_data2.get('multi_source_profile', {})
        if profile2:
            logger.info(f"\nSources used: {profile2.get('sources_used', [])}")
            
            hooks2 = profile2.get('personalization_hooks', [])
            if hooks2:
                logger.info(f"\n🎯 Personalization Hooks: {len(hooks2)}")
                for hook in hooks2[:3]:
                    logger.info(f"  - {hook['hook']}")
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("MULTI-SOURCE SCRAPING TEST COMPLETE")
        logger.info("=" * 60)
        
        if profile and hooks:
            logger.info("✅ Successfully scraped multiple sources")
            logger.info("✅ Generated personalization hooks")
            logger.info("✅ Ready for personalized outreach!")
        else:
            logger.info("⚠️ Limited results - check logs for issues")
        
        return scraped_data
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return None

if __name__ == "__main__":
    result = asyncio.run(test_multi_source_scraping())
    
    if result:
        # Save results for inspection
        with open('multi_source_test_results.json', 'w') as f:
            # Convert to JSON-serializable format
            def clean_for_json(obj):
                if isinstance(obj, dict):
                    return {k: clean_for_json(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [clean_for_json(v) for v in obj]
                elif hasattr(obj, '__dict__'):
                    return str(obj)
                else:
                    return obj
            
            json.dump(clean_for_json(result), f, indent=2)
            logger.info("\nFull results saved to multi_source_test_results.json")