"""
Focused web scraper that uses Serper Maps API and targeted scraping.
This replaces the complex multi-URL approach with a simpler, more effective strategy:
1. Get official website from Serper Maps
2. Scrape the official website
3. Get corporate info from Sunbiz
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .serper_client import SerperClient
from .sunbiz_scraper import SunbizScraper
from .enhanced_content_extractor import EnhancedContentExtractor
from .intelligent_web_navigator import IntelligentWebNavigator

logger = logging.getLogger(__name__)


class FocusedWebScraper:
    """
    Focused web scraper that gets high-quality data from specific sources.
    """
    
    def __init__(self):
        """Initialize the focused scraper with necessary components."""
        self.serper = SerperClient()
        self.sunbiz = SunbizScraper()
        self.content_extractor = EnhancedContentExtractor()
        self.web_navigator = IntelligentWebNavigator(max_pages=12)
        
    async def gather_business_data(self, company_name: str, address: str, 
                                  city: str = None, state: str = None,
                                  phone: str = None) -> Dict[str, Any]:
        """
        Gather comprehensive business data using focused sources.
        
        Args:
            company_name: Business name
            address: Street address
            city: City name
            state: State abbreviation
            phone: Known phone number (optional)
            
        Returns:
            Dictionary with all gathered business data
        """
        start_time = datetime.utcnow()
        
        # Build full address for better search results
        full_address = address
        if city:
            full_address += f", {city}"
        if state:
            full_address += f", {state}"
        
        result = {
            'company_name': company_name,
            'address': full_address,
            'maps_data': None,
            'website_content': None,
            'sunbiz_data': None,
            'extracted_info': {
                'website': None,
                'phone': phone,
                'hours': None,
                'rating': None,
                'owner_info': {},
                'business_type': None
            },
            'confidence_score': 0.0,
            'processing_time': 0
        }
        
        try:
            # Step 1: Get business info from Serper Maps
            logger.info(f"Searching Maps for: {company_name} at {full_address}")
            maps_data = await self.serper.search_maps(company_name, full_address)
            
            if maps_data:
                result['maps_data'] = maps_data
                result['extracted_info']['website'] = maps_data.get('website')
                result['extracted_info']['phone'] = maps_data.get('phone') or phone
                result['extracted_info']['hours'] = maps_data.get('hours')
                result['extracted_info']['rating'] = maps_data.get('rating')
                result['extracted_info']['business_type'] = maps_data.get('type')
                result['confidence_score'] += 0.4
                
                logger.info(f"Maps found website: {maps_data.get('website')}")
                
                # Step 2: Deep scrape the official website with intelligent navigation
                if maps_data.get('website'):
                    logger.info(f"Starting intelligent navigation of website: {maps_data['website']}")
                    
                    # Use the intelligent navigator for comprehensive scraping
                    nav_results = await self.web_navigator.navigate_and_extract(maps_data['website'])
                    
                    if nav_results and nav_results.get('pages_scraped') > 0:
                        result['website_content'] = {
                            'url': maps_data['website'],
                            'pages_scraped': nav_results['pages_scraped'],
                            'total_chars': nav_results['total_content_chars'],
                            'categories_found': list(nav_results['content_by_category'].keys()),
                            'team_members': nav_results.get('team_members', []),
                            'additional_contacts': nav_results.get('contact_info', {}),
                            'prioritized_content': nav_results.get('prioritized_content', ''),  # For AI
                            'errors': nav_results.get('errors', [])
                        }
                        
                        # Add team members to personnel tracking
                        if nav_results.get('team_members'):
                            if 'all_personnel' not in result['extracted_info']:
                                result['extracted_info']['all_personnel'] = []
                            
                            for member in nav_results['team_members']:
                                personnel_entry = f"{member.get('name', 'Unknown')}"
                                if member.get('title'):
                                    personnel_entry += f" ({member['title']})"
                                result['extracted_info']['all_personnel'].append(personnel_entry)
                            
                            logger.info(f"Found {len(nav_results['team_members'])} team members on website")
                        
                        result['confidence_score'] += 0.3
                        logger.info(f"Deep scraped {nav_results['pages_scraped']} pages, "
                                   f"{nav_results['total_content_chars']} total chars")
            else:
                logger.warning(f"No Maps results for: {company_name}")
            
            # Step 3: Get corporate info from Sunbiz (Florida businesses only)
            if state and state.upper() == 'FL':
                logger.info(f"Searching Sunbiz for: {company_name}")
                sunbiz_data = await self.sunbiz.search_business(company_name)
                
                if sunbiz_data:
                    result['sunbiz_data'] = sunbiz_data
                    
                    # Primary owner extraction - prioritize authorized persons over officers
                    if sunbiz_data.get('authorized_persons'):
                        # Use first authorized person as owner (these are typically the owners/managers)
                        auth_person = sunbiz_data['authorized_persons'][0]
                        result['extracted_info']['owner_info'] = {
                            'first_name': auth_person.get('first_name', ''),
                            'last_name': auth_person.get('last_name', ''),
                            'full_name': auth_person.get('full_name', ''),
                            'title': auth_person.get('title', ''),
                            'source': 'authorized_person'
                        }
                        result['confidence_score'] += 0.3
                        logger.info(f"Found {len(sunbiz_data['authorized_persons'])} authorized persons (using as owner)")
                        
                    elif sunbiz_data.get('officers'):
                        # Fallback to officers if no authorized persons
                        # Look for key titles that indicate ownership
                        owner_found = False
                        for officer in sunbiz_data['officers']:
                            title = officer.get('title', '').upper()
                            if any(t in title for t in ['PRESIDENT', 'CEO', 'OWNER', 'MANAGING', 'PRINCIPAL']):
                                result['extracted_info']['owner_info'] = {
                                    'first_name': officer.get('first_name', ''),
                                    'last_name': officer.get('last_name', ''),
                                    'full_name': officer.get('full_name', ''),
                                    'title': officer.get('title', ''),
                                    'source': 'officer'
                                }
                                owner_found = True
                                break
                        
                        # If no owner-like title found, use the first officer
                        if not owner_found and sunbiz_data['officers']:
                            officer = sunbiz_data['officers'][0]
                            result['extracted_info']['owner_info'] = {
                                'first_name': officer.get('first_name', ''),
                                'last_name': officer.get('last_name', ''),
                                'full_name': officer.get('full_name', ''),
                                'title': officer.get('title', ''),
                                'source': 'officer'
                            }
                        
                        if result['extracted_info']['owner_info']:
                            result['confidence_score'] += 0.25
                            logger.info(f"Found {len(sunbiz_data['officers'])} officers (using as owner)")
                    
                    # Store all people as additional context (for AI to use in personalization)
                    all_people = []
                    for person in sunbiz_data.get('authorized_persons', []):
                        all_people.append(f"{person.get('full_name', '')} ({person.get('title', '')})")
                    for officer in sunbiz_data.get('officers', []):
                        all_people.append(f"{officer.get('full_name', '')} ({officer.get('title', '')})")
                    
                    if all_people:
                        result['extracted_info']['all_personnel'] = all_people
                        logger.info(f"Total personnel found: {len(all_people)} people")
                    
                    # Log additional corporate info
                    if sunbiz_data.get('filing_info'):
                        filing = sunbiz_data['filing_info']
                        logger.info(f"Company FEIN: {filing.get('fein', 'Not found')}")
                        logger.info(f"Date Filed: {filing.get('date_filed', 'Not found')}")
                else:
                    logger.warning(f"No Sunbiz data found for: {company_name}")
            
            # Calculate final confidence score
            result['confidence_score'] = min(1.0, result['confidence_score'])
            
        except Exception as e:
            logger.error(f"Error gathering business data: {e}")
            result['error'] = str(e)
        
        # Add processing time
        result['processing_time'] = (datetime.utcnow() - start_time).total_seconds()
        
        logger.info(f"Focused gathering complete for {company_name}: "
                   f"confidence: {result['confidence_score']:.2%}, "
                   f"time: {result['processing_time']:.1f}s")
        
        return result


# Create a compatibility wrapper for existing code
class FocusedWebGatherer:
    """
    Drop-in replacement for the existing WebGatherer classes.
    Uses the focused approach with Maps and Sunbiz.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with focused scraper."""
        self.scraper = FocusedWebScraper()
        logger.info("Using FOCUSED web gatherer (Maps + Sunbiz)")
    
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
        Main method - uses focused gathering with Maps and Sunbiz.
        
        Args:
            company_name: Name of the business
            location: Location/address information
            additional_data: Additional context (phone, email, etc.)
            campaign_context: Campaign configuration
            
        Returns:
            Comprehensive data from focused sources
        """
        # Parse location into components if possible
        city = additional_data.get('city', '') if additional_data else ''
        state = additional_data.get('state', '') if additional_data else ''
        phone = additional_data.get('phone', '') if additional_data else ''
        
        # Use the focused scraper
        result = await self.scraper.gather_business_data(
            company_name=company_name,
            address=location,
            city=city,
            state=state,
            phone=phone
        )
        
        # Format for compatibility with existing code
        return self._format_for_compatibility(result)
    
    def _format_for_compatibility(self, focused_result: Dict) -> Dict[str, Any]:
        """
        Format the focused scraper result to be compatible with existing code.
        """
        extracted_info = focused_result.get('extracted_info', {})
        
        formatted = {
            'company_name': focused_result.get('company_name'),
            'location': focused_result.get('address'),
            'search_engine': 'serper_maps',
            'website_found': bool(extracted_info.get('website')),
            'website_url': extracted_info.get('website'),
            'website_data': focused_result.get('website_content', {}),
            
            # Multi-source profile with focused data
            'multi_source_profile': {
                'urls_scraped': focused_result.get('website_content', {}).get('pages_scraped', 0),
                'total_content_chars': focused_result.get('website_content', {}).get('total_chars', 0),
                
                # Owner information from Sunbiz
                'owner_info': extracted_info.get('owner_info', {}),
                
                # All personnel (from website and Sunbiz)
                'all_personnel': extracted_info.get('all_personnel', []),
                
                # Business details from Maps
                'business_details': {
                    'type': extracted_info.get('business_type'),
                    'rating': extracted_info.get('rating'),
                    'hours': extracted_info.get('hours')
                },
                
                # Contact information (combined from all sources)
                'contact_info': {
                    'phones': [extracted_info.get('phone')] if extracted_info.get('phone') else [],
                    'websites': [extracted_info.get('website')] if extracted_info.get('website') else [],
                    'emails': focused_result.get('website_content', {}).get('additional_contacts', {}).get('emails', [])
                },
                
                # Team members from website
                'team_members': focused_result.get('website_content', {}).get('team_members', []),
                
                # Combined content for AI processing - now using prioritized content
                'combined_content': focused_result.get('website_content', {}).get('prioritized_content', ''),
                
                # Registry data from Sunbiz
                'registry_data': focused_result.get('sunbiz_data', {})
            },
            
            'confidence_score': focused_result.get('confidence_score', 0.0),
            'processing_time': focused_result.get('processing_time', 0),
            'error': focused_result.get('error')
        }
        
        return formatted


# Test function
async def test_focused_scraper():
    """Test the focused scraper with a known business."""
    scraper = FocusedWebScraper()
    
    result = await scraper.gather_business_data(
        company_name="GATOR CITY MOTORS LLC",
        address="1700 N MAIN ST",
        city="GAINESVILLE",
        state="FL"
    )
    
    print("\n=== Focused Scraper Test Results ===")
    print(f"Company: {result['company_name']}")
    print(f"Website: {result['extracted_info']['website']}")
    print(f"Phone: {result['extracted_info']['phone']}")
    print(f"Owner: {result['extracted_info']['owner_info'].get('full_name', 'Not found')}")
    print(f"Confidence: {result['confidence_score']:.2%}")
    print(f"Processing time: {result['processing_time']:.1f}s")
    
    return result


if __name__ == "__main__":
    asyncio.run(test_focused_scraper())