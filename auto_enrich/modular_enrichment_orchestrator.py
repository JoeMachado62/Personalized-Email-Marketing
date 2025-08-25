"""
Modular Enrichment Orchestrator

This orchestrates the enrichment pipeline based on user-selected processing steps.
It respects the processing configuration and executes only enabled steps.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .processing_config import ProcessingConfiguration
from .serper_client import SerperClient
from .sunbiz_scraper import SunbizScraper
from .enhanced_content_extractor import EnhancedContentExtractor
from .intelligent_web_navigator import IntelligentWebNavigator
from .social_media_scraper import SocialMediaScraper
from .data_interpreter import interpret_scraped_data

logger = logging.getLogger(__name__)


class ModularEnrichmentOrchestrator:
    """
    Orchestrates enrichment processing based on user configuration.
    Executes only the processing steps that are enabled.
    """
    
    def __init__(self, processing_config: Optional[Dict[str, Any]] = None):
        """
        Initialize orchestrator with processing configuration.
        
        Args:
            processing_config: Configuration dict with enabled_steps list
        """
        self.config = ProcessingConfiguration()
        
        # Apply user configuration if provided
        if processing_config and processing_config.get('enabled_steps'):
            # Disable all steps first
            for step_id in self.config.steps:
                self.config.steps[step_id].enabled = False
            
            # Enable only selected steps
            for step_id in processing_config['enabled_steps']:
                if step_id in self.config.steps:
                    self.config.steps[step_id].enabled = True
            
            self.config._update_enabled_steps()
        
        # Initialize processors
        self.serper = SerperClient()
        self.sunbiz = SunbizScraper()
        self.content_extractor = EnhancedContentExtractor()
        self.web_navigator = IntelligentWebNavigator(max_pages=12)
        self.social_scraper = SocialMediaScraper()
        
        logger.info(f"🔧 Modular orchestrator initialized with {len(self.config.enabled_steps)} enabled steps: {list(self.config.enabled_steps)}")
    
    async def enrich_business_data(self, company_name: str, address: str = "",
                                 city: str = "", state: str = "", phone: str = "",
                                 additional_data: Optional[Dict] = None,
                                 campaign_context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Execute enrichment based on configured processing steps.
        
        Args:
            company_name: Business name
            address: Street address
            city: City name
            state: State abbreviation
            phone: Known phone number
            additional_data: Additional input data
            campaign_context: Campaign context and preferences
            
        Returns:
            Dictionary with enrichment results
        """
        start_time = datetime.utcnow()
        
        # Build full address for better search results
        full_address = address
        if city:
            full_address += f", {city}"
        if state:
            full_address += f", {state}"
        
        # Initialize result structure
        result = {
            'company_name': company_name,
            'address': full_address,
            'processing_steps_used': list(self.config.enabled_steps),
            'maps_data': None,
            'website_content': None,
            'social_media_data': None,
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
        
        # Execute processing steps in dependency order
        execution_order = self.config.get_processing_plan()
        logger.info(f"🚀 [START] Processing {company_name} with steps: {execution_order}")
        
        step_results = {}
        
        for step_id in execution_order:
            try:
                step_start_time = datetime.utcnow()
                step_result = await self._execute_processing_step(
                    step_id, company_name, full_address, city, state, phone,
                    additional_data, campaign_context, step_results
                )
                
                if step_result:
                    step_results[step_id] = step_result
                    step_time = (datetime.utcnow() - step_start_time).total_seconds()
                    logger.info(f"✅ [{step_id.upper()}] Completed in {step_time:.1f}s")
                else:
                    logger.warning(f"❌ [{step_id.upper()}] No results returned")
                    
            except Exception as e:
                logger.error(f"❌ [{step_id.upper()}] Failed: {e}")
                step_results[step_id] = {'error': str(e)}
        
        # Consolidate results from all executed steps
        result = self._consolidate_step_results(result, step_results)
        
        # Calculate final confidence score
        result['confidence_score'] = self._calculate_confidence_score(step_results)
        result['processing_time'] = (datetime.utcnow() - start_time).total_seconds()
        
        # Log final summary
        self._log_enrichment_summary(result)
        
        return result
    
    async def _execute_processing_step(self, step_id: str, company_name: str, 
                                     full_address: str, city: str, state: str, 
                                     phone: str, additional_data: Optional[Dict],
                                     campaign_context: Optional[Dict],
                                     previous_results: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute a single processing step.
        
        Args:
            step_id: ID of the step to execute
            company_name: Business name
            full_address: Full address string
            city: City name
            state: State abbreviation 
            phone: Phone number
            additional_data: Additional input data
            campaign_context: Campaign context
            previous_results: Results from previous steps
            
        Returns:
            Results from this processing step
        """
        if step_id == 'sunbiz_search':
            return await self._execute_sunbiz_search(company_name, state)
            
        elif step_id == 'serper_maps':
            return await self._execute_serper_maps(company_name, full_address)
            
        elif step_id == 'website_scraping':
            # Check for website URL from Maps or CSV data
            website_url = None
            
            # First check if Maps found a website
            maps_data = previous_results.get('serper_maps')
            if maps_data and maps_data.get('website'):
                website_url = maps_data['website']
                logger.info(f"🌐 [WEBSITE_SCRAPING] Using website from Maps: {website_url}")
            else:
                # Check if website URL was provided in CSV data
                if additional_data and additional_data.get('website'):
                    website_url = additional_data['website']
                    logger.info(f"🌐 [WEBSITE_SCRAPING] Using website from CSV: {website_url}")
                # TODO: Could also check for extracted website from other sources
            
            if website_url:
                return await self._execute_website_scraping(website_url)
            else:
                logger.warning(f"🌐 [WEBSITE_SCRAPING] SKIPPED - No website URL available")
                logger.info(f"💡 [WEBSITE_SCRAPING] Tip: Enable Google Maps search or include website URLs in your CSV")
                return None
                
        elif step_id == 'social_media_search':
            return await self._execute_social_media_search(company_name, full_address)
            
        elif step_id == 'ai_content_generation':
            # This step uses all available data
            return await self._execute_ai_content_generation(
                company_name, previous_results, campaign_context
            )
            
        elif step_id == 'contact_enrichment':
            # Depends on website_scraping results
            website_data = previous_results.get('website_scraping')
            if website_data:
                return await self._execute_contact_enrichment(website_data, previous_results)
            else:
                logger.warning(f"📧 [CONTACT_ENRICHMENT] SKIPPED - No website data available")
                return None
                
        elif step_id == 'competitor_analysis':
            return await self._execute_competitor_analysis(company_name, previous_results)
            
        else:
            logger.warning(f"Unknown processing step: {step_id}")
            return None
    
    async def _execute_sunbiz_search(self, company_name: str, state: str) -> Optional[Dict[str, Any]]:
        """Execute Sunbiz corporate search."""
        if state and state.upper() == 'FL':
            logger.info(f"🏢 [SUNBIZ_SEARCH] Searching for: {company_name}")
            sunbiz_data = await self.sunbiz.search_business(company_name)
            if sunbiz_data:
                officer_count = len(sunbiz_data.get('officers', []))
                auth_count = len(sunbiz_data.get('authorized_persons', []))
                logger.info(f"🏢 [SUNBIZ_SEARCH] Found {officer_count} officers, {auth_count} authorized persons")
                return sunbiz_data
            else:
                logger.warning(f"🏢 [SUNBIZ_SEARCH] No data found for {company_name}")
        else:
            logger.info(f"🏢 [SUNBIZ_SEARCH] SKIPPED - Not a Florida business (state: {state})")
        return None
    
    async def _execute_serper_maps(self, company_name: str, full_address: str) -> Optional[Dict[str, Any]]:
        """Execute Google Maps business search via Serper."""
        logger.info(f"🗺️ [SERPER_MAPS] Searching for: {company_name} at {full_address}")
        maps_data = await self.serper.search_maps(company_name, full_address)
        
        if maps_data:
            logger.info(f"🗺️ [SERPER_MAPS] Found - Website: {maps_data.get('website')}, Phone: {maps_data.get('phone')}, Rating: {maps_data.get('rating')}")
            return maps_data
        else:
            logger.warning(f"🗺️ [SERPER_MAPS] No results for {company_name}")
        return None
    
    async def _execute_website_scraping(self, website_url: str) -> Optional[Dict[str, Any]]:
        """Execute website content scraping."""
        logger.info(f"🌐 [WEBSITE_SCRAPING] Scraping: {website_url}")
        
        try:
            nav_results = await self.web_navigator.navigate_and_extract(website_url)
            
            if nav_results and nav_results.get('pages_scraped', 0) > 0:
                website_data = {
                    'url': website_url,
                    'pages_scraped': nav_results['pages_scraped'],
                    'total_chars': nav_results['total_content_chars'],
                    'categories_found': list(nav_results['content_by_category'].keys()),
                    'team_members': nav_results.get('team_members', []),
                    'additional_contacts': nav_results.get('contact_info', {}),
                    'prioritized_content': nav_results.get('prioritized_content', ''),
                    'errors': nav_results.get('errors', [])
                }
                
                logger.info(f"🌐 [WEBSITE_SCRAPING] Scraped {nav_results['pages_scraped']} pages, "
                           f"{nav_results['total_content_chars']} chars")
                return website_data
            else:
                logger.warning(f"🌐 [WEBSITE_SCRAPING] No content extracted from {website_url}")
                
        except Exception as e:
            logger.error(f"🌐 [WEBSITE_SCRAPING] Error scraping {website_url}: {e}")
            
        return None
    
    async def _execute_social_media_search(self, company_name: str, location: str) -> Optional[Dict[str, Any]]:
        """Execute social media profile discovery."""
        logger.info(f"📱 [SOCIAL_MEDIA_SEARCH] Discovering profiles for: {company_name}")
        
        try:
            social_data = await self.social_scraper.get_social_context_for_ai(
                company_name, location
            )
            
            if social_data['has_social_presence']:
                profiles_found = len(social_data['active_platforms'])
                content_chars = social_data['total_social_content_chars']
                logger.info(f"📱 [SOCIAL_MEDIA_SEARCH] Found {profiles_found} profiles, {content_chars} content chars")
                return social_data
            else:
                logger.info(f"📱 [SOCIAL_MEDIA_SEARCH] No social media profiles found")
                
        except Exception as e:
            logger.error(f"📱 [SOCIAL_MEDIA_SEARCH] Error: {e}")
            
        return None
    
    async def _execute_ai_content_generation(self, company_name: str, 
                                           previous_results: Dict[str, Any],
                                           campaign_context: Optional[Dict]) -> Optional[Dict[str, Any]]:
        """Execute AI content generation using all available data."""
        logger.info(f"🤖 [AI_CONTENT_GENERATION] Generating content for: {company_name}")
        
        # Build comprehensive data package for AI
        scraped_data = self._build_scraped_data_for_ai(company_name, previous_results, campaign_context)
        
        try:
            interpreted_data = await interpret_scraped_data(scraped_data, campaign_context)
            
            email_content = interpreted_data.get('generated_content', {})
            if email_content:
                ai_result = {
                    'subject': email_content.get('subject', {}).get('raw_response', ''),
                    'icebreaker': email_content.get('icebreaker', {}).get('raw_response', ''),
                    'hot_button': email_content.get('hot_button', {}).get('raw_response', ''),
                    'confidence_scores': interpreted_data.get('confidence_scores', {})
                }
                
                logger.info(f"🤖 [AI_CONTENT_GENERATION] Generated content - Subject: {'✅' if ai_result['subject'] else '❌'}, "
                           f"Icebreaker: {'✅' if ai_result['icebreaker'] else '❌'}, "
                           f"Hot Button: {'✅' if ai_result['hot_button'] else '❌'}")
                return ai_result
            else:
                logger.warning(f"🤖 [AI_CONTENT_GENERATION] No content generated")
                
        except Exception as e:
            logger.error(f"🤖 [AI_CONTENT_GENERATION] Error: {e}")
            
        return None
    
    async def _execute_contact_enrichment(self, website_data: Dict, 
                                        previous_results: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute additional contact information enrichment."""
        logger.info(f"📧 [CONTACT_ENRICHMENT] Enhancing contact information")
        
        # Extract additional contacts from website data
        additional_contacts = website_data.get('additional_contacts', {})
        contact_result = {
            'emails': additional_contacts.get('emails', []),
            'phones': additional_contacts.get('phones', []),
            'team_members': website_data.get('team_members', [])
        }
        
        # Try to match owner information with contacts
        sunbiz_data = previous_results.get('sunbiz_search')
        if sunbiz_data and contact_result['emails']:
            owner_info = self._extract_owner_from_sunbiz(sunbiz_data)
            if owner_info and owner_info.get('first_name'):
                # Try to find owner email
                owner_first = owner_info['first_name'].lower()
                for email in contact_result['emails']:
                    if owner_first in email.lower():
                        contact_result['owner_email'] = email
                        logger.info(f"📧 [CONTACT_ENRICHMENT] Matched owner email: {email}")
                        break
        
        return contact_result if any(contact_result.values()) else None
    
    async def _execute_competitor_analysis(self, company_name: str,
                                         previous_results: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute competitive intelligence analysis."""
        logger.info(f"🏆 [COMPETITOR_ANALYSIS] Analyzing competition for: {company_name}")
        
        # This is a placeholder for competitive analysis
        # In a real implementation, this would research competitors
        competitor_result = {
            'analysis_performed': True,
            'competitors': [],
            'market_position': 'unknown',
            'note': 'Competitor analysis not fully implemented yet'
        }
        
        return competitor_result
    
    def _consolidate_step_results(self, base_result: Dict[str, Any], 
                                step_results: Dict[str, Any]) -> Dict[str, Any]:
        """Consolidate results from all processing steps into final result."""
        
        # Maps data
        if 'serper_maps' in step_results:
            maps_data = step_results['serper_maps']
            base_result['maps_data'] = maps_data
            if maps_data:
                base_result['extracted_info']['website'] = maps_data.get('website')
                base_result['extracted_info']['phone'] = maps_data.get('phone') or base_result['extracted_info']['phone']
                base_result['extracted_info']['hours'] = maps_data.get('hours')
                base_result['extracted_info']['rating'] = maps_data.get('rating')
                base_result['extracted_info']['business_type'] = maps_data.get('type')
        
        # Website data
        if 'website_scraping' in step_results:
            base_result['website_content'] = step_results['website_scraping']
        
        # Social media data
        if 'social_media_search' in step_results:
            base_result['social_media_data'] = step_results['social_media_search']
        
        # Sunbiz data and owner extraction
        if 'sunbiz_search' in step_results:
            sunbiz_data = step_results['sunbiz_search']
            base_result['sunbiz_data'] = sunbiz_data
            if sunbiz_data:
                owner_info = self._extract_owner_from_sunbiz(sunbiz_data)
                if owner_info:
                    base_result['extracted_info']['owner_info'] = owner_info
        
        # AI generated content
        if 'ai_content_generation' in step_results:
            ai_data = step_results['ai_content_generation']
            if ai_data:
                base_result['generated_content'] = {
                    'subject': ai_data.get('subject', ''),
                    'icebreaker': ai_data.get('icebreaker', ''),
                    'hot_button': ai_data.get('hot_button', ''),
                    'confidence_scores': ai_data.get('confidence_scores', {})
                }
        
        # Contact enrichment
        if 'contact_enrichment' in step_results:
            contact_data = step_results['contact_enrichment']
            if contact_data:
                base_result['contact_enrichment'] = contact_data
        
        return base_result
    
    def _extract_owner_from_sunbiz(self, sunbiz_data: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Extract owner information from Sunbiz data."""
        # Prioritize authorized persons over officers
        if sunbiz_data.get('authorized_persons'):
            auth_person = sunbiz_data['authorized_persons'][0]
            return {
                'first_name': auth_person.get('first_name', ''),
                'last_name': auth_person.get('last_name', ''),
                'full_name': auth_person.get('full_name', ''),
                'title': auth_person.get('title', ''),
                'source': 'authorized_person'
            }
        elif sunbiz_data.get('officers'):
            # Look for owner-like titles first
            for officer in sunbiz_data['officers']:
                title = officer.get('title', '').upper()
                if any(t in title for t in ['PRESIDENT', 'CEO', 'OWNER', 'MANAGING', 'PRINCIPAL']):
                    return {
                        'first_name': officer.get('first_name', ''),
                        'last_name': officer.get('last_name', ''),
                        'full_name': officer.get('full_name', ''),
                        'title': officer.get('title', ''),
                        'source': 'officer'
                    }
            # Use first officer if no owner-like title found
            if sunbiz_data['officers']:
                officer = sunbiz_data['officers'][0]
                return {
                    'first_name': officer.get('first_name', ''),
                    'last_name': officer.get('last_name', ''),
                    'full_name': officer.get('full_name', ''),
                    'title': officer.get('title', ''),
                    'source': 'officer'
                }
        return None
    
    def _build_scraped_data_for_ai(self, company_name: str, 
                                 step_results: Dict[str, Any],
                                 campaign_context: Optional[Dict] = None) -> Dict[str, Any]:
        """Build scraped data structure for AI processing."""
        scraped_data = {
            'company_name': company_name,
            'search_engine': 'modular_orchestrator',
            'website_found': False,
            'website_url': None,
            'website_data': {},
            'campaign_context': campaign_context,  # Include campaign context for AI
            'multi_source_profile': {
                'sources_used': [],
                'owner_info': {},
                'all_personnel': [],
                'business_details': {},
                'contact_info': {'phones': [], 'websites': [], 'emails': []},
                'combined_content': '',
                'social_context': {}
            }
        }
        
        # Add data from each completed step
        if 'serper_maps' in step_results and step_results['serper_maps']:
            maps_data = step_results['serper_maps']
            scraped_data['website_found'] = bool(maps_data.get('website'))
            scraped_data['website_url'] = maps_data.get('website')
            scraped_data['multi_source_profile']['sources_used'].append('google_maps')
            scraped_data['multi_source_profile']['business_details'] = {
                'type': maps_data.get('type'),
                'rating': maps_data.get('rating'),
                'hours': maps_data.get('hours')
            }
            if maps_data.get('website'):
                scraped_data['multi_source_profile']['contact_info']['websites'].append(maps_data['website'])
            if maps_data.get('phone'):
                scraped_data['multi_source_profile']['contact_info']['phones'].append(maps_data['phone'])
        
        if 'website_scraping' in step_results and step_results['website_scraping']:
            website_data = step_results['website_scraping']
            scraped_data['website_data'] = website_data
            scraped_data['multi_source_profile']['sources_used'].append('website_multi_page')
            scraped_data['multi_source_profile']['combined_content'] = website_data.get('prioritized_content', '')
            
            # Add contact info from website
            additional_contacts = website_data.get('additional_contacts', {})
            scraped_data['multi_source_profile']['contact_info']['emails'].extend(
                additional_contacts.get('emails', [])
            )
            scraped_data['multi_source_profile']['contact_info']['phones'].extend(
                additional_contacts.get('phones', [])
            )
        
        if 'sunbiz_search' in step_results and step_results['sunbiz_search']:
            sunbiz_data = step_results['sunbiz_search']
            scraped_data['multi_source_profile']['sources_used'].append('sunbiz')
            scraped_data['multi_source_profile']['registry_data'] = sunbiz_data
            
            # Extract owner info
            owner_info = self._extract_owner_from_sunbiz(sunbiz_data)
            if owner_info:
                scraped_data['multi_source_profile']['owner_info'] = owner_info
        
        if 'social_media_search' in step_results and step_results['social_media_search']:
            social_data = step_results['social_media_search']
            scraped_data['multi_source_profile']['sources_used'].append('social_media')
            scraped_data['multi_source_profile']['social_context'] = social_data
        
        return scraped_data
    
    def _calculate_confidence_score(self, step_results: Dict[str, Any]) -> float:
        """Calculate overall confidence score based on completed steps."""
        confidence = 0.0
        
        # Each successful step adds to confidence
        if 'serper_maps' in step_results and step_results['serper_maps']:
            confidence += 0.3
        if 'website_scraping' in step_results and step_results['website_scraping']:
            confidence += 0.2
        if 'sunbiz_search' in step_results and step_results['sunbiz_search']:
            confidence += 0.3
        if 'social_media_search' in step_results and step_results['social_media_search']:
            confidence += 0.1
        if 'ai_content_generation' in step_results and step_results['ai_content_generation']:
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def _log_enrichment_summary(self, result: Dict[str, Any]) -> None:
        """Log final enrichment summary."""
        website = result['extracted_info'].get('website')
        owner_info = result['extracted_info'].get('owner_info', {})
        owner_name = owner_info.get('full_name', 'Not found')
        content_chars = result.get('website_content', {}).get('total_chars', 0)
        social_profiles = len(result.get('social_media_data', {}).get('active_platforms', []))
        
        logger.info(f"📊 [FINAL] {result['company_name']} Results:")
        logger.info(f"  🌐 Website: {website or 'Not found'}")
        logger.info(f"  👤 Owner: {owner_name}")
        logger.info(f"  📄 Content: {content_chars} characters")
        logger.info(f"  📱 Social Profiles: {social_profiles}")
        logger.info(f"  ⭐ Confidence: {result['confidence_score']:.1%}")
        logger.info(f"  ⏱️ Time: {result['processing_time']:.1f}s")
        logger.info(f"  🔧 Steps Used: {result['processing_steps_used']}")


# Compatibility wrapper for existing code
class ModularWebGatherer:
    """
    Drop-in replacement for FocusedWebGatherer that uses modular processing.
    """
    
    def __init__(self, processing_config: Optional[Dict[str, Any]] = None):
        """Initialize with processing configuration."""
        self.orchestrator = ModularEnrichmentOrchestrator(processing_config)
        logger.info("Using MODULAR web gatherer with configurable processing steps")
    
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
        Main method using modular processing.
        
        Args:
            company_name: Name of the business
            location: Location/address information
            additional_data: Additional context (phone, email, etc.)
            campaign_context: Campaign configuration (includes processing_config)
            
        Returns:
            Comprehensive data from enabled processing steps
        """
        # Parse location and additional data
        city = additional_data.get('city', '') if additional_data else ''
        state = additional_data.get('state', '') if additional_data else ''
        phone = additional_data.get('phone', '') if additional_data else ''
        
        # Execute modular enrichment
        result = await self.orchestrator.enrich_business_data(
            company_name=company_name,
            address=location,
            city=city,
            state=state,
            phone=phone,
            additional_data=additional_data,
            campaign_context=campaign_context
        )
        
        # Format for compatibility with existing enricher.py expectations
        return self._format_for_compatibility(result)
    
    def _format_for_compatibility(self, modular_result: Dict) -> Dict[str, Any]:
        """
        Format modular result to be compatible with existing enricher.py code.
        """
        extracted_info = modular_result.get('extracted_info', {})
        
        formatted = {
            'company_name': modular_result.get('company_name'),
            'location': modular_result.get('address'),
            'search_engine': 'modular_orchestrator',
            'website_found': bool(extracted_info.get('website')),
            'website_url': extracted_info.get('website'),
            'website_data': modular_result.get('website_content', {}),
            
            # Multi-source profile with modular data
            'multi_source_profile': {
                'sources_used': modular_result.get('processing_steps_used', []),
                'urls_scraped': modular_result.get('website_content', {}).get('pages_scraped', 0),
                'total_content_chars': modular_result.get('website_content', {}).get('total_chars', 0),
                
                # Owner information
                'owner_info': extracted_info.get('owner_info', {}),
                
                # Business details from Maps
                'business_details': {
                    'type': extracted_info.get('business_type'),
                    'rating': extracted_info.get('rating'),
                    'hours': extracted_info.get('hours')
                },
                
                # Contact information
                'contact_info': {
                    'phones': [extracted_info.get('phone')] if extracted_info.get('phone') else [],
                    'websites': [extracted_info.get('website')] if extracted_info.get('website') else [],
                    'emails': modular_result.get('website_content', {}).get('additional_contacts', {}).get('emails', [])
                },
                
                # Team members from website
                'team_members': modular_result.get('website_content', {}).get('team_members', []),
                
                # Combined content for AI processing
                'combined_content': modular_result.get('website_content', {}).get('prioritized_content', ''),
                
                # Registry data from Sunbiz
                'registry_data': modular_result.get('sunbiz_data', {}),
                
                # Social media context
                'social_context': modular_result.get('social_media_data', {})
            },
            
            # Generated content from AI
            'generated_content': modular_result.get('generated_content', {}),
            
            'confidence_score': modular_result.get('confidence_score', 0.0),
            'processing_time': modular_result.get('processing_time', 0),
            'error': modular_result.get('error')
        }
        
        return formatted