"""
Basic enrichment without LLM - extracts data using patterns and rules.
Fallback when no OpenAI API key is configured.
"""

import re
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class BasicEnrichment:
    """
    Provides basic enrichment without AI/LLM.
    Uses pattern matching and rules to extract information.
    """
    
    def __init__(self):
        """Initialize basic enrichment."""
        self.owner_titles = [
            'owner', 'ceo', 'president', 'founder', 'director',
            'manager', 'proprietor', 'principal', 'partner'
        ]
        
    async def enrich_without_llm(self, scraped_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich data without using LLM.
        
        Args:
            scraped_data: Data from web scraping
            
        Returns:
            Enriched data with basic extraction
        """
        logger.info("Using basic enrichment (no LLM API key configured)")
        
        company_name = scraped_data.get('company_name', 'Business')
        location = scraped_data.get('location', '')
        
        # Extract from search results and website data
        website_data = scraped_data.get('website_data', {})
        search_results = scraped_data.get('search_results', [])
        gmb_data = scraped_data.get('gmb_data', {})
        
        # Extract owner information
        owner_info = self._extract_owner_from_content(website_data, search_results)
        
        # Extract business details
        business_details = self._extract_business_details(website_data, search_results, gmb_data)
        
        # Identify basic pain points
        pain_points = self._identify_basic_pain_points(scraped_data)
        
        # Generate basic email content
        email_content = self._generate_basic_email_content(
            company_name, 
            location,
            owner_info,
            business_details,
            pain_points
        )
        
        return {
            'company_name': company_name,
            'location': location,
            'timestamp': datetime.utcnow().isoformat(),
            'source_data': {
                'website_found': bool(scraped_data.get('website_url')),
                'search_results_count': len(search_results),
                'data_quality': self._assess_quality(scraped_data)
            },
            'extracted_info': {
                'owner': owner_info,
                'business_details': business_details,
                'pain_points': pain_points
            },
            'generated_content': email_content,
            'confidence_scores': {
                'overall': self._calculate_confidence(scraped_data),
                'owner': 50 if owner_info.get('first_name') else 20,
                'content': 70 if website_data else 30
            }
        }
    
    def _extract_owner_from_content(self, website_data: Dict, search_results: List) -> Dict:
        """Extract owner name from content using patterns."""
        owner = {
            'first_name': None,
            'last_name': None,
            'title': None,
            'confidence': 0
        }
        
        # Combine all text content
        all_text = ""
        if website_data:
            all_text += str(website_data.get('text', ''))
            all_text += str(website_data.get('description', ''))
        
        for result in search_results[:3]:
            all_text += str(result.get('snippet', ''))
        
        if not all_text:
            return owner
        
        # Look for owner patterns
        patterns = [
            r'(?:owned by|owner[:\s]+|proprietor[:\s]+)([A-Z][a-z]+ [A-Z][a-z]+)',
            r'(?:CEO|President|Founder|Director)[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)',
            r'([A-Z][a-z]+ [A-Z][a-z]+),?\s+(?:Owner|CEO|President|Founder)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, all_text, re.IGNORECASE)
            if matches:
                name_parts = matches[0].strip().split()
                if len(name_parts) >= 2:
                    owner['first_name'] = name_parts[0]
                    owner['last_name'] = ' '.join(name_parts[1:])
                    owner['confidence'] = 60
                    logger.info(f"Found potential owner: {owner['first_name']} {owner['last_name']}")
                    break
        
        return owner
    
    def _extract_business_details(self, website_data: Dict, search_results: List, gmb_data: Dict) -> Dict:
        """Extract business details from available data."""
        details = {
            'specialization': '',
            'years_in_business': None,
            'unique_features': [],
            'inventory_focus': '',
            'business_type': gmb_data.get('type', '')
        }
        
        # Extract from snippets
        for result in search_results[:3]:
            snippet = result.get('snippet', '').lower()
            
            # Look for specialization keywords
            if 'specialize' in snippet or 'expert' in snippet or 'focus' in snippet:
                details['specialization'] = snippet[:200]
            
            # Look for years in business
            year_match = re.search(r'(\d+)\s+years?\s+(?:in business|of experience|serving)', snippet)
            if year_match:
                details['years_in_business'] = int(year_match.group(1))
            
            # Look for inventory/product mentions
            if 'cars' in snippet or 'vehicles' in snippet or 'auto' in snippet:
                if 'used' in snippet:
                    details['inventory_focus'] = 'Used vehicles'
                elif 'new' in snippet:
                    details['inventory_focus'] = 'New vehicles'
                elif 'luxury' in snippet:
                    details['inventory_focus'] = 'Luxury vehicles'
        
        return details
    
    def _identify_basic_pain_points(self, scraped_data: Dict) -> Dict:
        """Identify basic pain points from data."""
        pain_points = {
            'observed_issues': [],
            'missing_features': [],
            'opportunities': []
        }
        
        # Check for missing website
        if not scraped_data.get('website_url'):
            pain_points['observed_issues'].append('No website found')
            pain_points['opportunities'].append('Establish online presence')
        
        # Check for missing contact info
        website_data = scraped_data.get('website_data', {})
        contact_info = website_data.get('contact_info', {})
        
        if not contact_info.get('emails'):
            pain_points['missing_features'].append('No email contact found')
        
        if not contact_info.get('phones'):
            pain_points['missing_features'].append('No phone number on website')
        
        # Check search visibility
        if len(scraped_data.get('search_results', [])) < 3:
            pain_points['observed_issues'].append('Low search visibility')
            pain_points['opportunities'].append('Improve SEO and online marketing')
        
        # Check for GMB presence
        if not scraped_data.get('gmb_data'):
            pain_points['missing_features'].append('No Google My Business listing')
            pain_points['opportunities'].append('Claim and optimize GMB listing')
        
        return pain_points
    
    def _generate_basic_email_content(self, company_name: str, location: str, 
                                     owner_info: Dict, business_details: Dict,
                                     pain_points: Dict) -> Dict:
        """Generate basic email content without AI."""
        
        # Create subject line
        if owner_info.get('last_name'):
            subject = f"Quick question for {owner_info['last_name']} at {company_name}"
        elif location:
            subject = f"Helping {company_name} in {location} grow online"
        else:
            subject = f"Growth opportunity for {company_name}"
        
        # Create icebreaker
        if business_details.get('years_in_business'):
            icebreaker = f"I noticed {company_name} has been serving {location} for {business_details['years_in_business']} years. That's an impressive track record in the auto industry."
        elif business_details.get('specialization'):
            icebreaker = f"I came across {company_name} while researching auto dealers in {location}. Your focus on {business_details.get('inventory_focus', 'quality vehicles')} caught my attention."
        else:
            icebreaker = f"I noticed {company_name} while researching businesses in {location}. Your dealership stood out to me."
        
        # Identify hot button
        if pain_points['observed_issues']:
            hot_button = pain_points['observed_issues'][0]
        elif pain_points['opportunities']:
            hot_button = f"Opportunity: {pain_points['opportunities'][0]}"
        else:
            hot_button = "Increasing online visibility and lead generation"
        
        return {
            'subject': {'raw_response': subject},
            'icebreaker': {'raw_response': icebreaker},
            'hot_button': {'raw_response': hot_button}
        }
    
    def _assess_quality(self, scraped_data: Dict) -> str:
        """Assess data quality."""
        score = 0
        
        if scraped_data.get('website_url'):
            score += 30
        if scraped_data.get('website_data'):
            score += 20
        if scraped_data.get('gmb_data'):
            score += 20
        if len(scraped_data.get('search_results', [])) > 3:
            score += 15
        if scraped_data.get('extracted_contacts'):
            score += 15
        
        if score >= 70:
            return 'high'
        elif score >= 40:
            return 'medium'
        else:
            return 'low'
    
    def _calculate_confidence(self, scraped_data: Dict) -> float:
        """Calculate overall confidence score."""
        score = 0.0
        
        if scraped_data.get('website_url'):
            score += 0.3
        if scraped_data.get('website_data'):
            score += 0.2
        if scraped_data.get('gmb_data'):
            score += 0.2
        if len(scraped_data.get('search_results', [])) > 3:
            score += 0.15
        if scraped_data.get('extracted_contacts'):
            score += 0.15
        
        return min(1.0, score)