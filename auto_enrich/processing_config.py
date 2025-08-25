"""
Modular Processing Configuration System
Allows users to configure which enrichment steps to run based on their data needs.
"""

from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class ProcessingStep:
    """Configuration for a single processing step."""
    id: str
    name: str
    description: str
    category: str
    dependencies: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    enabled: bool = True
    required_inputs: List[str] = field(default_factory=list)
    optional_inputs: List[str] = field(default_factory=list)
    estimated_time_seconds: int = 10
    api_cost_estimate: float = 0.0


class ProcessingConfiguration:
    """
    Manages modular processing configuration for enrichment pipeline.
    """
    
    def __init__(self):
        """Initialize with default processing steps."""
        self.steps = self._define_default_steps()
        self.enabled_steps = set()
        self._update_enabled_steps()
    
    def _define_default_steps(self) -> Dict[str, ProcessingStep]:
        """Define all available processing steps."""
        return {
            # Data source steps
            'sunbiz_search': ProcessingStep(
                id='sunbiz_search',
                name='Sunbiz Corporate Search',
                description='Search Florida Sunbiz database for corporate records and owner information',
                category='data_sources',
                required_inputs=['company_name'],
                optional_inputs=['state'],
                outputs=['owner_first_name', 'owner_last_name', 'officers', 'filing_date', 'fein'],
                estimated_time_seconds=15,
                api_cost_estimate=0.0
            ),
            
            'serper_maps': ProcessingStep(
                id='serper_maps',
                name='Google Maps Business Search',
                description='Search Google Maps/Places for business information and website',
                category='data_sources', 
                required_inputs=['company_name'],
                optional_inputs=['address', 'city', 'state'],
                outputs=['website', 'phone', 'rating', 'hours', 'business_type'],
                estimated_time_seconds=8,
                api_cost_estimate=0.01
            ),
            
            'website_scraping': ProcessingStep(
                id='website_scraping',
                name='Website Content Scraping',
                description='Scrape and extract content from business website for context',
                category='content_extraction',
                dependencies=[],  # Can work independently if website URLs are provided in CSV
                required_inputs=['website'],
                outputs=['website_content', 'team_members', 'services', 'about_info'],
                estimated_time_seconds=25,
                api_cost_estimate=0.0
            ),
            
            'social_media_search': ProcessingStep(
                id='social_media_search', 
                name='Social Media Discovery',
                description='Find and scrape business social media profiles for additional context',
                category='content_extraction',
                required_inputs=['company_name'],
                optional_inputs=['address', 'city', 'state'],
                outputs=['social_profiles', 'social_content', 'social_themes'],
                estimated_time_seconds=45,
                api_cost_estimate=0.0
            ),
            
            # AI processing steps
            'ai_content_generation': ProcessingStep(
                id='ai_content_generation',
                name='AI Content Generation', 
                description='Generate personalized email content using AI with collected context',
                category='ai_processing',
                dependencies=[],  # Can work with any available data, but should run last
                required_inputs=['company_name'],
                optional_inputs=['website_content', 'social_content', 'owner_info', 'business_info'],
                outputs=['email_subject', 'email_icebreaker', 'hot_button_topics'],
                estimated_time_seconds=12,
                api_cost_estimate=0.02
            ),
            
            # Optional enhancement steps
            'contact_enrichment': ProcessingStep(
                id='contact_enrichment',
                name='Contact Information Enhancement',
                description='Find additional contact details like owner email and phone',
                category='data_enhancement', 
                dependencies=['website_scraping'],
                required_inputs=['website_content'],
                optional_inputs=['owner_first_name', 'owner_last_name'],
                outputs=['owner_email', 'owner_phone', 'additional_contacts'],
                estimated_time_seconds=20,
                api_cost_estimate=0.0,
                enabled=False  # Optional by default
            ),
            
            'competitor_analysis': ProcessingStep(
                id='competitor_analysis',
                name='Competitive Intelligence',
                description='Research competitors and market positioning for better personalization',
                category='market_intelligence',
                required_inputs=['company_name', 'business_type'],
                optional_inputs=['industry_context'],
                outputs=['competitors', 'market_position', 'differentiators'],
                estimated_time_seconds=30,
                api_cost_estimate=0.03,
                enabled=False  # Optional by default
            )
        }
    
    def _update_enabled_steps(self):
        """Update the set of enabled steps."""
        self.enabled_steps = {step_id for step_id, step in self.steps.items() if step.enabled}
    
    def enable_step(self, step_id: str) -> bool:
        """
        Enable a processing step.
        
        Args:
            step_id: ID of the step to enable
            
        Returns:
            True if step was enabled successfully
        """
        if step_id not in self.steps:
            logger.warning(f"Unknown processing step: {step_id}")
            return False
        
        self.steps[step_id].enabled = True
        self._update_enabled_steps()
        logger.info(f"Enabled processing step: {step_id}")
        return True
    
    def disable_step(self, step_id: str) -> bool:
        """
        Disable a processing step.
        
        Args:
            step_id: ID of the step to disable
            
        Returns:
            True if step was disabled successfully
        """
        if step_id not in self.steps:
            logger.warning(f"Unknown processing step: {step_id}")
            return False
        
        # Check if any enabled steps depend on this one
        dependents = self.get_dependent_steps(step_id)
        if dependents:
            logger.warning(f"Cannot disable {step_id}: required by {dependents}")
            return False
        
        self.steps[step_id].enabled = False
        self._update_enabled_steps()
        logger.info(f"Disabled processing step: {step_id}")
        return True
    
    def get_dependent_steps(self, step_id: str) -> List[str]:
        """Get list of enabled steps that depend on the given step."""
        dependents = []
        for other_step_id, step in self.steps.items():
            if step.enabled and step_id in step.dependencies:
                dependents.append(other_step_id)
        return dependents
    
    def get_processing_plan(self) -> List[str]:
        """
        Get the execution order of enabled steps respecting dependencies.
        
        Returns:
            List of step IDs in execution order
        """
        enabled_steps = {step_id: self.steps[step_id] for step_id in self.enabled_steps}
        execution_order = []
        processed = set()
        
        def can_execute(step_id: str) -> bool:
            """Check if step can be executed (all dependencies processed)."""
            step = enabled_steps[step_id]
            return all(dep in processed or dep not in enabled_steps for dep in step.dependencies)
        
        # Keep adding steps until all are processed
        while len(processed) < len(enabled_steps):
            added_this_round = False
            
            for step_id in enabled_steps:
                # Skip AI content generation until all other steps are done
                if step_id == 'ai_content_generation' and len(processed) < len(enabled_steps) - 1:
                    continue
                    
                if step_id not in processed and can_execute(step_id):
                    execution_order.append(step_id)
                    processed.add(step_id)
                    added_this_round = True
            
            if not added_this_round:
                # Check if only AI content generation is left
                remaining = set(enabled_steps.keys()) - processed
                if remaining == {'ai_content_generation'}:
                    execution_order.append('ai_content_generation')
                    processed.add('ai_content_generation')
                else:
                    # Circular dependency or missing dependency
                    logger.error(f"Cannot resolve dependencies for steps: {remaining}")
                    break
        
        return execution_order
    
    def validate_configuration(self, available_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the current configuration against available input data.
        
        Args:
            available_data: Dictionary of available input data fields
            
        Returns:
            Validation result with warnings and suggestions
        """
        validation = {
            'valid': True,
            'warnings': [],
            'suggestions': [],
            'missing_required_inputs': [],
            'estimated_total_time': 0,
            'estimated_total_cost': 0.0
        }
        
        available_fields = set(available_data.keys()) if available_data else set()
        
        for step_id in self.enabled_steps:
            step = self.steps[step_id]
            
            # Check required inputs
            missing_required = [inp for inp in step.required_inputs if inp not in available_fields]
            if missing_required:
                validation['missing_required_inputs'].extend([f"{step_id}: {inp}" for inp in missing_required])
                validation['valid'] = False
            
            # Add to time and cost estimates
            validation['estimated_total_time'] += step.estimated_time_seconds
            validation['estimated_total_cost'] += step.api_cost_estimate
        
        # Add suggestions based on available data
        if 'website' in available_fields and 'website_scraping' not in self.enabled_steps:
            validation['suggestions'].append("You have website data - consider enabling Website Content Scraping")
        
        if 'owner_first_name' in available_fields and 'sunbiz_search' in self.enabled_steps:
            validation['suggestions'].append("You already have owner data - consider disabling Sunbiz Search")
        
        if not available_fields.intersection({'company_name', 'business_name', 'dealer_name'}):
            validation['warnings'].append("No company name field detected - enrichment may fail")
        
        return validation
    
    def get_step_recommendations(self, data_quality: Dict[str, Any]) -> Dict[str, str]:
        """
        Get step recommendations based on data quality assessment.
        
        Args:
            data_quality: Assessment of input data quality
            
        Returns:
            Recommendations for each step
        """
        recommendations = {}
        
        # Analyze what data is already present
        has_website = data_quality.get('has_website', False)
        has_owner_names = data_quality.get('has_owner_names', False) 
        has_contact_info = data_quality.get('has_contact_info', False)
        data_completeness = data_quality.get('completeness_percentage', 0)
        
        if has_owner_names:
            recommendations['sunbiz_search'] = "SKIP - Owner names already present"
        else:
            recommendations['sunbiz_search'] = "RECOMMENDED - Will find owner information"
            
        if has_website:
            recommendations['serper_maps'] = "OPTIONAL - Websites already available"
            recommendations['website_scraping'] = "RECOMMENDED - Scrape existing websites for context"
        else:
            recommendations['serper_maps'] = "RECOMMENDED - Will discover business websites"
            recommendations['website_scraping'] = "AUTO - Will run if websites found"
            
        recommendations['social_media_search'] = "OPTIONAL - Adds social media context for personalization"
        recommendations['ai_content_generation'] = "REQUIRED - Generates personalized content"
        
        if data_completeness < 50:
            recommendations['contact_enrichment'] = "RECOMMENDED - Low data completeness"
        else:
            recommendations['contact_enrichment'] = "OPTIONAL - Data seems fairly complete"
            
        return recommendations
    
    def create_preset_configuration(self, preset_name: str) -> bool:
        """
        Apply a preset configuration.
        
        Args:
            preset_name: Name of the preset to apply
            
        Returns:
            True if preset was applied successfully
        """
        presets = {
            'minimal': ['ai_content_generation'],  # Only AI generation
            'basic': ['serper_maps', 'website_scraping', 'ai_content_generation'],
            'standard': ['sunbiz_search', 'serper_maps', 'website_scraping', 'ai_content_generation'],
            'comprehensive': ['sunbiz_search', 'serper_maps', 'website_scraping', 'social_media_search', 'ai_content_generation'],
            'premium': ['sunbiz_search', 'serper_maps', 'website_scraping', 'social_media_search', 'contact_enrichment', 'ai_content_generation'],
            'research': ['sunbiz_search', 'serper_maps', 'website_scraping', 'social_media_search', 'competitor_analysis', 'ai_content_generation']
        }
        
        if preset_name not in presets:
            logger.warning(f"Unknown preset: {preset_name}")
            return False
        
        # Disable all steps first
        for step_id in self.steps:
            self.steps[step_id].enabled = False
        
        # Enable preset steps
        for step_id in presets[preset_name]:
            if step_id in self.steps:
                self.steps[step_id].enabled = True
        
        self._update_enabled_steps()
        logger.info(f"Applied preset configuration: {preset_name}")
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary."""
        return {
            'enabled_steps': list(self.enabled_steps),
            'steps': {
                step_id: {
                    'enabled': step.enabled,
                    'name': step.name,
                    'description': step.description,
                    'category': step.category,
                    'estimated_time_seconds': step.estimated_time_seconds,
                    'api_cost_estimate': step.api_cost_estimate
                }
                for step_id, step in self.steps.items()
            },
            'execution_order': self.get_processing_plan()
        }
    
    def from_dict(self, config_data: Dict[str, Any]):
        """Load configuration from dictionary."""
        enabled_steps = config_data.get('enabled_steps', [])
        
        # Reset all steps to disabled
        for step_id in self.steps:
            self.steps[step_id].enabled = False
        
        # Enable specified steps
        for step_id in enabled_steps:
            if step_id in self.steps:
                self.steps[step_id].enabled = True
        
        self._update_enabled_steps()