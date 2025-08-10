"""
Intelligent Search Query Optimizer
Constructs optimal search queries based on available data and campaign objectives
"""

import logging
from typing import Dict, List, Any, Optional
import re

logger = logging.getLogger(__name__)


class SearchQueryOptimizer:
    """
    Builds intelligent search queries based on:
    1. Available data in CSV
    2. Campaign objectives
    3. Industry context
    4. Desired information to find
    """
    
    def __init__(self, campaign_context: Dict[str, Any]):
        """
        Initialize with campaign context from user input.
        
        Args:
            campaign_context: Dictionary containing:
                - campaign_goal: What the user is trying to achieve
                - target_information: What data they want to find
                - industry_context: Optional industry-specific terms
                - personalization_focus: What to focus on for personalization
        """
        self.campaign_context = campaign_context
        self.query_templates = self._load_query_templates()
    
    def _load_query_templates(self) -> Dict[str, List[str]]:
        """
        Load search query templates for different objectives.
        These templates help construct effective searches.
        """
        return {
            # Find official website and contact info
            'official_presence': [
                '{company_name} {location}',
                '{company_name} {city} {state}',
                '"{company_name}" official website',
                '{company_name} contact information'
            ],
            
            # Find owner/leadership information
            'leadership': [
                '{company_name} owner',
                '{company_name} CEO president founder',
                '"{company_name}" leadership team',
                'site:linkedin.com {company_name} {location}'
            ],
            
            # Find social media presence
            'social_media': [
                '{company_name} {location} facebook',
                '{company_name} instagram twitter',
                'site:facebook.com "{company_name}"',
                '{company_name} social media'
            ],
            
            # Find reviews and reputation
            'reputation': [
                '{company_name} reviews {location}',
                '{company_name} yelp google reviews',
                '"{company_name}" customer feedback',
                '{company_name} complaints testimonials'
            ],
            
            # Find recent news and updates
            'recent_activity': [
                '{company_name} {location} news {current_year}',
                '"{company_name}" announcement update',
                '{company_name} {location} "recent" OR "latest"',
                'site:news.google.com {company_name}'
            ],
            
            # Industry-specific searches
            'industry_specific': [
                '{company_name} {industry_terms}',
                '"{company_name}" {service_keywords}',
                '{company_name} {location} {business_type}'
            ]
        }
    
    def build_search_queries(self, record_data: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Build a prioritized list of search queries for a record.
        
        Args:
            record_data: Dictionary with available data fields like:
                - company_name: Business name
                - location/address: Location information
                - city, state, zip: Address components
                - phone: Phone number
                - industry: Industry/business type (if available)
                
        Returns:
            List of search query dictionaries with:
                - query: The search string
                - purpose: What this search aims to find
                - priority: 1-5 (1 being highest)
        """
        queries = []
        
        # Extract and clean data
        company_name = self._clean_company_name(record_data.get('company_name', ''))
        location = self._build_location_string(record_data)
        city = record_data.get('city', '')
        state = record_data.get('state', '')
        
        # Determine which query types to use based on campaign context
        target_info = self.campaign_context.get('target_information', [])
        
        # Priority 1: Find official presence
        if 'website' in target_info or 'contact' in target_info:
            queries.extend(self._build_queries_from_template(
                'official_presence',
                company_name=company_name,
                location=location,
                city=city,
                state=state,
                priority=1
            ))
        
        # Priority 2: Find leadership if needed
        if 'owner' in target_info or 'decision_maker' in target_info:
            queries.extend(self._build_queries_from_template(
                'leadership',
                company_name=company_name,
                location=location,
                priority=2
            ))
        
        # Priority 3: Social media for personalization
        if self.campaign_context.get('personalization_focus') == 'social':
            queries.extend(self._build_queries_from_template(
                'social_media',
                company_name=company_name,
                location=location,
                priority=3
            ))
        
        # Priority 4: Reviews for pain points
        if 'pain_points' in target_info or 'reviews' in target_info:
            queries.extend(self._build_queries_from_template(
                'reputation',
                company_name=company_name,
                location=location,
                priority=4
            ))
        
        # Priority 5: Recent activity for icebreakers
        if self.campaign_context.get('personalization_focus') == 'recent_activity':
            import datetime
            current_year = datetime.datetime.now().year
            queries.extend(self._build_queries_from_template(
                'recent_activity',
                company_name=company_name,
                location=location,
                current_year=current_year,
                priority=5
            ))
        
        # Add industry-specific searches if context provided
        if self.campaign_context.get('industry_context'):
            queries.extend(self._build_industry_queries(
                company_name, 
                location,
                self.campaign_context['industry_context']
            ))
        
        # Sort by priority and limit
        queries.sort(key=lambda x: x['priority'])
        
        # Return top queries based on campaign needs
        max_queries = self.campaign_context.get('max_searches_per_record', 3)
        return queries[:max_queries]
    
    def _clean_company_name(self, name: str) -> str:
        """
        Clean company name for better search results.
        Remove common suffixes that might limit results.
        """
        # Remove common business suffixes for broader search
        suffixes_to_remove = [
            r'\s+INC\.?$',
            r'\s+LLC\.?$',
            r'\s+LTD\.?$',
            r'\s+CORP\.?$',
            r'\s+CORPORATION$',
            r'\s+COMPANY$',
            r'\s+CO\.?$',
            r'\s+INCORPORATED$',
            r'\s+LIMITED$'
        ]
        
        cleaned = name
        for suffix in suffixes_to_remove:
            cleaned = re.sub(suffix, '', cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()
    
    def _build_location_string(self, record_data: Dict[str, str]) -> str:
        """Build location string from available location data."""
        parts = []
        
        if record_data.get('city'):
            parts.append(record_data['city'])
        if record_data.get('state'):
            parts.append(record_data['state'])
        
        # If no city/state, try to parse from address
        if not parts and record_data.get('address'):
            # Extract city, state from address
            address_parts = record_data['address'].split(',')
            if len(address_parts) >= 2:
                parts = [p.strip() for p in address_parts[-2:]]
        
        return ' '.join(parts)
    
    def _build_queries_from_template(self, template_key: str, priority: int = 3, **kwargs) -> List[Dict[str, Any]]:
        """Build queries from a template with variable substitution."""
        queries = []
        templates = self.query_templates.get(template_key, [])
        
        for template in templates:
            try:
                query = template.format(**kwargs)
                queries.append({
                    'query': query,
                    'purpose': template_key,
                    'priority': priority
                })
            except KeyError:
                # Skip templates that need variables we don't have
                continue
        
        return queries
    
    def _build_industry_queries(self, company_name: str, location: str, 
                                industry_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build industry-specific search queries."""
        queries = []
        
        # Handle both string and dictionary formats
        if isinstance(industry_context, str):
            # Convert string to dictionary format
            industry_terms = industry_context.split(',') if industry_context else []
            industry_terms = [term.strip() for term in industry_terms]
            service_keywords = []
            business_type = industry_context
        else:
            industry_terms = industry_context.get('terms', [])
            service_keywords = industry_context.get('services', [])
            business_type = industry_context.get('type', '')
        
        # Build queries using industry context
        if industry_terms:
            query = f'{company_name} {location} {" ".join(industry_terms[:2])}'
            queries.append({
                'query': query,
                'purpose': 'industry_specific',
                'priority': 3
            })
        
        if service_keywords:
            query = f'"{company_name}" {" OR ".join(service_keywords[:3])}'
            queries.append({
                'query': query,
                'purpose': 'service_discovery',
                'priority': 4
            })
        
        return queries


class SmartSearchBuilder:
    """
    Uses AI to build optimal search queries based on CSV data analysis.
    """
    
    @staticmethod
    async def analyze_and_build_queries(
        record_data: Dict[str, str],
        campaign_context: Dict[str, Any],
        csv_sample: Optional[List[Dict[str, str]]] = None
    ) -> List[str]:
        """
        Use AI to analyze the data and build smart search queries.
        
        Args:
            record_data: Single record to search for
            campaign_context: User's campaign goals and context
            csv_sample: Sample of other records for pattern recognition
            
        Returns:
            List of optimized search queries
        """
        from auto_enrich.data_interpreter import DataInterpreter
        
        # Build AI prompt for query generation
        prompt = f"""
        Analyze this business data and generate optimal search queries.
        
        RECORD DATA:
        {record_data}
        
        CAMPAIGN GOALS:
        - Find: {campaign_context.get('target_information', [])}
        - Purpose: {campaign_context.get('campaign_goal', '')}
        - Focus: {campaign_context.get('personalization_focus', '')}
        
        REQUIREMENTS:
        1. Generate 3-5 search queries that will find the most relevant information
        2. Prioritize queries likely to return official websites and social media
        3. Include queries for finding decision makers if needed
        4. Consider the business type and location
        5. Remove corporate suffixes (INC, LLC) for broader results
        
        Return queries as a JSON list of strings.
        """
        
        # Use AI to generate queries
        # This would integrate with your existing AI infrastructure
        # For now, return the optimizer's queries
        optimizer = SearchQueryOptimizer(campaign_context)
        queries = optimizer.build_search_queries(record_data)
        
        return [q['query'] for q in queries]


# System prompt template for AI-assisted query building
QUERY_BUILDER_SYSTEM_PROMPT = """
You are an expert at constructing search queries for business research.
Your goal is to find the most relevant information about businesses based on limited data.

When building search queries:
1. Start with broad queries using company name and location
2. Add specific queries for social media profiles
3. Include queries for finding decision makers and contact info
4. Use site: operators for targeted searches (LinkedIn, Facebook, etc.)
5. Remove corporate suffixes (INC, LLC, CORP) for better results
6. Use quotes for exact matches when the company name is unique
7. Combine location terms effectively (city, state)
8. Consider industry-specific terms if provided

Always aim for queries that will return:
- Official company website
- Social media profiles
- Reviews and reputation data
- Leadership/owner information
- Recent news or updates
"""


def get_default_campaign_context() -> Dict[str, Any]:
    """
    Get default campaign context for testing or when user doesn't specify.
    """
    return {
        'campaign_goal': 'Generate personalized outreach emails',
        'target_information': ['website', 'owner', 'contact', 'social_media'],
        'personalization_focus': 'recent_activity',
        'max_searches_per_record': 3,
        'industry_context': None
    }


# Example usage
if __name__ == "__main__":
    # Test with Broadway Auto Brokers
    test_record = {
        'company_name': 'BROADWAY AUTO BROKERS INC',
        'city': 'ALACHUA',
        'state': 'FL',
        'phone': '(352)415-0010'
    }
    
    context = get_default_campaign_context()
    optimizer = SearchQueryOptimizer(context)
    
    queries = optimizer.build_search_queries(test_record)
    
    print("Generated Search Queries:")
    for q in queries:
        print(f"Priority {q['priority']}: {q['query']}")
        print(f"  Purpose: {q['purpose']}")