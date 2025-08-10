"""
User-configurable enrichment prompts and settings.
Allows users to customize what data to extract and how to interpret it.
"""

from pydantic import BaseModel
from typing import Dict, Optional, List
from enum import Enum


class EnrichmentField(str, Enum):
    """Fields that can be enriched"""
    WEBSITE = "website"
    OWNER_NAME = "owner_name"
    OWNER_EMAIL = "owner_email"
    OWNER_PHONE = "owner_phone"
    BUSINESS_DETAILS = "business_details"
    EMAIL_SUBJECT = "email_subject"
    EMAIL_ICEBREAKER = "email_icebreaker"
    HOT_BUTTON = "hot_button"
    CUSTOM = "custom"


class EnrichmentConfig(BaseModel):
    """Configuration for enrichment process"""
    
    # Fields to enrich
    fields_to_enrich: List[EnrichmentField] = [
        EnrichmentField.WEBSITE,
        EnrichmentField.OWNER_NAME,
        EnrichmentField.EMAIL_SUBJECT,
        EnrichmentField.EMAIL_ICEBREAKER,
        EnrichmentField.HOT_BUTTON
    ]
    
    # Search settings
    search_depth: int = 5  # Number of search results to analyze
    scrape_timeout: int = 30  # Seconds to wait for page load
    
    # Custom prompts for data extraction
    custom_prompts: Optional[Dict[str, str]] = None
    
    # Example custom prompts
    example_prompts: Dict[str, str] = {
        "owner_extraction": "Find the owner or decision maker's name and title",
        "business_focus": "What type of vehicles does this dealer specialize in?",
        "unique_selling_point": "What makes this dealership unique?",
        "pain_points": "What business challenges might this dealer face?",
        "email_tone": "Professional but friendly, mention specific details about their business"
    }
    
    # Cost controls
    max_cost_per_record: float = 0.02
    use_caching: bool = True
    
    # Data quality requirements
    min_confidence_score: float = 0.5
    require_website: bool = False
    require_owner_name: bool = False
    
    class Config:
        schema_extra = {
            "example": {
                "fields_to_enrich": ["website", "owner_name", "email_subject"],
                "search_depth": 3,
                "custom_prompts": {
                    "owner_extraction": "Find the general manager or owner's name",
                    "email_tone": "Casual and friendly, focus on helping their business grow"
                },
                "max_cost_per_record": 0.01,
                "min_confidence_score": 0.6
            }
        }


class EnrichmentRequest(BaseModel):
    """Request to enrich data with custom configuration"""
    
    job_id: str
    config: Optional[EnrichmentConfig] = None
    test_mode: bool = False  # If true, only process first 5 records
    
    
class EnrichmentPrompts(BaseModel):
    """User-defined prompts for enrichment"""
    
    # Data extraction prompts
    extract_owner: Optional[str] = None
    extract_business_details: Optional[str] = None
    identify_pain_points: Optional[str] = None
    
    # Content generation prompts  
    email_subject_template: Optional[str] = None
    email_icebreaker_template: Optional[str] = None
    hot_button_template: Optional[str] = None
    
    # Examples for users
    examples: Dict[str, str] = {
        "extract_owner": "Find the owner, CEO, or general manager's full name and title from the website",
        "extract_business_details": "Identify their specialization (e.g., luxury cars, trucks, fleet sales)",
        "identify_pain_points": "Based on their website, what digital marketing improvements could help them?",
        "email_subject_template": "Create a subject line mentioning their city and dealership name",
        "email_icebreaker_template": "Mention something specific from their website or recent updates",
        "hot_button_template": "Identify their biggest competitive challenge based on local market"
    }