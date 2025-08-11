"""
Enhanced web scraper that combines Serper API with multi-URL scraping.
This replaces the basic single-URL approach with comprehensive multi-source data gathering.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from .multi_url_scraper import MultiURLScraper
from .serper_client import SerperClient
from .business_registry_parser import BusinessRegistryParser

logger = logging.getLogger(__name__)


class EnhancedWebGatherer:
    """
    Enhanced web data gatherer that:
    1. Uses Serper API to get 20-30 search results
    2. Intelligently categorizes and prioritizes URLs
    3. Scrapes multiple URLs in parallel
    4. Aggregates content from all sources
    5. Extracts structured data including owner names
    """
    
    def __init__(self):
        """Initialize the enhanced gatherer with all components."""
        self.multi_scraper = MultiURLScraper(max_urls_per_company=12, parallel_limit=3)
        self.serper_client = SerperClient()
        self.registry_parser = BusinessRegistryParser()
    
    async def gather_comprehensive_data(self, company_name: str, location: str = "",
                                       additional_data: Optional[Dict] = None,
                                       campaign_context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Main method: Gather comprehensive data from multiple sources.
        
        Args:
            company_name: Name of the business
            location: Location/address information
            additional_data: Additional context (phone, email, etc.)
            campaign_context: Campaign configuration
            
        Returns:
            Comprehensive data from all sources
        """
        start_time = datetime.utcnow()
        
        # Use the multi-URL scraper which handles everything
        result = await self.multi_scraper.scrape_company(company_name, location, additional_data)
        
        # Add timing information
        result['processing_time'] = (datetime.utcnow() - start_time).total_seconds()
        
        # Format the result for compatibility with existing system
        formatted_result = self._format_for_compatibility(result)
        
        # Log summary
        logger.info(f"Enhanced gathering complete for {company_name}: "
                   f"{result['urls_scraped']} URLs scraped, "
                   f"{result['aggregated_content'].get('total_content_length', 0)} chars collected, "
                   f"confidence: {result['confidence_score']:.2%}, "
                   f"time: {result['processing_time']:.1f}s")
        
        return formatted_result
    
    def _format_for_compatibility(self, multi_scraper_result: Dict) -> Dict[str, Any]:
        """
        Format the multi-scraper result to be compatible with existing code.
        
        Args:
            multi_scraper_result: Result from multi-URL scraper
            
        Returns:
            Formatted result compatible with existing enrichment pipeline
        """
        # Extract key data from the comprehensive result
        extracted_data = multi_scraper_result.get('extracted_data', {})
        aggregated = multi_scraper_result.get('aggregated_content', {})
        
        # Find the primary website URL
        website_url = None
        if aggregated.get('company_website', {}).get('source_urls'):
            website_url = aggregated['company_website']['source_urls'][0]
        
        # Build the compatible format
        formatted = {
            'company_name': multi_scraper_result.get('company_name'),
            'location': multi_scraper_result.get('location'),
            
            # Search results info
            'search_results': [],  # We'll populate this below
            'search_results_count': multi_scraper_result.get('search_results_count', 0),
            'search_engine': 'serper_enhanced',
            
            # Website info
            'website_found': bool(website_url),
            'website_url': website_url,
            'website_data': {},
            
            # Multi-source profile (NEW - this is where the magic happens!)
            'multi_source_profile': {
                'sources_used': multi_scraper_result.get('categorized_sources', {}),
                'urls_scraped': multi_scraper_result.get('urls_scraped', 0),
                'total_content_chars': aggregated.get('total_content_length', 0),
                
                # Owner information (from business registry)
                'owner_info': extracted_data.get('owner_info', {}),
                
                # Business details
                'business_details': extracted_data.get('business_details', {}),
                
                # Contact information
                'contact_info': extracted_data.get('contact_info', {}),
                
                # Social media profiles
                'social_media': extracted_data.get('social_media', {}),
                
                # Reviews and ratings
                'reviews': extracted_data.get('reviews', []),
                
                # Recent activity/news
                'recent_activity': extracted_data.get('news_mentions', []),
                
                # Pain points identified
                'pain_points': extracted_data.get('pain_points', []),
                
                # Achievements and accolades
                'achievements': extracted_data.get('achievements', []),
                
                # Aggregated content for AI processing
                'combined_content': aggregated.get('combined_text', ''),
                
                # Business registry data (parsed)
                'registry_data': aggregated.get('business_registry', {}).get('parsed_data', {})
            },
            
            # Confidence score
            'confidence_score': multi_scraper_result.get('confidence_score', 0.0),
            
            # Processing metadata
            'processing_time': multi_scraper_result.get('processing_time', 0),
            'timestamp': multi_scraper_result.get('search_timestamp'),
            
            # Error handling
            'error': multi_scraper_result.get('error')
        }
        
        # Add categorized search results for debugging/transparency
        if multi_scraper_result.get('categorized_sources'):
            formatted['search_results_categorized'] = multi_scraper_result['categorized_sources']
        
        return formatted


# Create a compatibility wrapper for existing code
class SerperWebGatherer:
    """
    Drop-in replacement for the existing SerperWebGatherer that uses enhanced multi-URL scraping.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with enhanced gatherer."""
        self.enhanced_gatherer = EnhancedWebGatherer()
        logger.info("Using ENHANCED multi-URL web gatherer")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, *args):
        """Async context manager exit."""
        pass
    
    async def search_and_gather(self, company_name: str, location: str = "",
                               additional_data: Optional[Dict] = None,
                               campaign_context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Main method - now uses enhanced multi-URL gathering.
        
        Args:
            company_name: Name of the business
            location: Location/address information
            additional_data: Additional context
            campaign_context: Campaign configuration
            
        Returns:
            Comprehensive data from multiple sources
        """
        return await self.enhanced_gatherer.gather_comprehensive_data(
            company_name, location, additional_data, campaign_context
        )


# Helper function for testing
async def test_enhanced_scraping():
    """Test the enhanced scraping with a sample company."""
    gatherer = EnhancedWebGatherer()
    
    # Test with a known Florida business
    result = await gatherer.gather_comprehensive_data(
        company_name="REED MITCHELL CARS INC",
        location="920 NW 2ND ST GAINESVILLE FL"
    )
    
    print("\n=== Enhanced Scraping Test Results ===")
    print(f"Company: {result['company_name']}")
    print(f"Search results: {result['search_results_count']}")
    print(f"URLs scraped: {result['multi_source_profile']['urls_scraped']}")
    print(f"Total content: {result['multi_source_profile']['total_content_chars']} chars")
    print(f"Confidence: {result['confidence_score']:.2%}")
    
    if result['multi_source_profile']['owner_info']:
        owner = result['multi_source_profile']['owner_info']
        print(f"\nOwner found: {owner.get('full_name', 'Unknown')}")
        print(f"  Title: {owner.get('title', 'Unknown')}")
    
    if result['multi_source_profile']['pain_points']:
        print(f"\nPain points identified:")
        for point in result['multi_source_profile']['pain_points']:
            print(f"  - {point}")
    
    return result


if __name__ == "__main__":
    # For testing
    asyncio.run(test_enhanced_scraping())