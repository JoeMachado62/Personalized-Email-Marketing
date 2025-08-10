"""
Professional email templates and prompts for car dealership marketing.

This module contains industry-specific templates, prompt engineering optimizations,
and content variations for different tones and contexts.
"""

from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass


class EmailTone(Enum):
    """Email tone variations."""
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    URGENT = "urgent"


class DealershipType(Enum):
    """Types of car dealerships."""
    USED_CAR = "used_car"
    NEW_CAR = "new_car"
    LUXURY = "luxury"
    COMMERCIAL = "commercial"
    MOTORCYCLE = "motorcycle"
    RV_BOAT = "rv_boat"


@dataclass
class EmailTemplate:
    """Email template structure."""
    subject_template: str
    icebreaker_template: str
    hot_button_template: str
    tone: EmailTone
    dealership_type: Optional[DealershipType] = None


class DealershipPrompts:
    """Optimized prompts for dealership marketing content generation."""
    
    # Base system prompts for different tones
    SYSTEM_PROMPTS = {
        EmailTone.PROFESSIONAL: """You are a professional B2B marketing specialist who creates compelling, results-driven content for automotive dealerships. Your writing is:
- Direct and business-focused
- Data-driven when possible
- Respectful and authoritative
- Focused on ROI and business outcomes
- Industry-aware and credible""",
        
        EmailTone.FRIENDLY: """You are a warm, approachable marketing consultant who builds genuine relationships with dealership owners. Your writing is:
- Conversational and personable
- Empathetic to business challenges
- Community-focused
- Encouraging and supportive
- Authentic and relatable""",
        
        EmailTone.URGENT: """You are a results-oriented marketing strategist who creates compelling, action-driven content. Your writing is:
- Time-sensitive and compelling
- Opportunity-focused
- Competitive and market-aware
- Solutions-oriented
- Persuasive without being pushy"""
    }
    
    # Token-optimized base prompt template
    BASE_PROMPT_TEMPLATE = """Context: {dealership_name} in {city}
Website: {website}
Owner: {owner_info}
Business: {dealership_type} dealership
{extra_context}

Generate 3 email variations ({tone1}, {tone2}, {tone3}) with:

1. SUBJECT: 6-8 words, personalized with owner name
2. ICEBREAKER: 2-3 sentences referencing specific dealership details
3. HOT_BUTTON: 1 sentence identifying key business challenge

Format:
TONE_{tone1}_SUBJECT: [subject]
TONE_{tone1}_ICEBREAKER: [icebreaker]
TONE_{tone1}_HOT_BUTTON: [hot_button]

TONE_{tone2}_SUBJECT: [subject]
TONE_{tone2}_ICEBREAKER: [icebreaker]
TONE_{tone2}_HOT_BUTTON: [hot_button]

TONE_{tone3}_SUBJECT: [subject]
TONE_{tone3}_ICEBREAKER: [icebreaker]
TONE_{tone3}_HOT_BUTTON: [hot_button]"""

    # Industry-specific hot button topics
    HOT_BUTTON_TOPICS = {
        DealershipType.USED_CAR: [
            "inventory management and turnover optimization",
            "online visibility and lead generation",
            "customer trust building and reputation management",
            "financing partner relationships and approval rates",
            "seasonal sales fluctuations and cash flow",
            "competitive pricing and market positioning",
            "digital marketing ROI and cost per acquisition",
            "customer retention and repeat business"
        ],
        
        DealershipType.NEW_CAR: [
            "manufacturer compliance and certification requirements",
            "allocation improvements and inventory planning",
            "service department profitability and retention",
            "digital transformation and online sales process",
            "customer satisfaction scores and manufacturer standards",
            "parts and accessories revenue optimization",
            "technician recruitment and retention",
            "warranty claim efficiency and profit recovery"
        ],
        
        DealershipType.LUXURY: [
            "premium customer experience and white-glove service",
            "exclusive inventory access and allocation management",
            "high-net-worth customer acquisition and retention",
            "boutique service experience and personalization",
            "brand reputation management and luxury positioning",
            "concierge services and customer lifecycle management",
            "exclusive events and VIP customer engagement",
            "premium financing and lease program optimization"
        ]
    }
    
    # Icebreaker templates by dealership type
    ICEBREAKER_TEMPLATES = {
        DealershipType.USED_CAR: [
            "I noticed {dealership_name} has been serving {city} for {years_context}. Your focus on {specialization} really stands out in the local market.",
            "Your {current_inventory_focus} inventory at {dealership_name} caught my attention. The {city} market seems perfect for your approach.",
            "I've been researching successful used car dealers in {city}, and {dealership_name}'s {unique_selling_point} is impressive."
        ],
        
        DealershipType.NEW_CAR: [
            "Congratulations on {dealership_name}'s {manufacturer} certification achievements. Your {city} location has excellent visibility.",
            "I see {dealership_name} is a {manufacturer} dealer in {city}. Your service department expansion shows great strategic thinking.",
            "Your {dealership_name} team's commitment to {manufacturer} standards in {city} is evident from your customer reviews."
        ],
        
        DealershipType.LUXURY: [
            "The luxury automotive market in {city} is evolving, and {dealership_name}'s positioning with {premium_brands} is strategic.",
            "I've been following the {city} luxury car market, and {dealership_name}'s approach to {premium_service_aspect} is noteworthy.",
            "Your {dealership_name} brand represents the premium standard in {city}. The {luxury_feature} really differentiates your offering."
        ]
    }
    
    @classmethod
    def get_system_prompt(cls, tone: EmailTone) -> str:
        """Get system prompt for specified tone."""
        return cls.SYSTEM_PROMPTS.get(tone, cls.SYSTEM_PROMPTS[EmailTone.PROFESSIONAL])
    
    @classmethod
    def build_optimized_prompt(
        cls,
        dealership_name: str,
        city: str,
        website: Optional[str] = None,
        owner_name: Optional[str] = None,
        dealership_type: DealershipType = DealershipType.USED_CAR,
        extra_context: Optional[str] = None,
        tones: List[EmailTone] = None
    ) -> str:
        """Build token-optimized prompt for multiple email variations."""
        
        if tones is None:
            tones = [EmailTone.PROFESSIONAL, EmailTone.FRIENDLY, EmailTone.URGENT]
        
        # Ensure we have exactly 3 tones
        while len(tones) < 3:
            tones.append(EmailTone.PROFESSIONAL)
        tones = tones[:3]
        
        # Format owner information
        owner_info = f"Owner: {owner_name}" if owner_name else "Owner: [Name from email]"
        
        # Format website
        website_info = website or "Not available"
        
        # Format dealership type
        dealership_type_str = dealership_type.value.replace("_", " ").title()
        
        # Prepare context
        context = extra_context or "Standard automotive dealership"
        
        return cls.BASE_PROMPT_TEMPLATE.format(
            dealership_name=dealership_name,
            city=city,
            website=website_info,
            owner_info=owner_info,
            dealership_type=dealership_type_str,
            extra_context=context,
            tone1=tones[0].value.upper(),
            tone2=tones[1].value.upper(),
            tone3=tones[2].value.upper()
        )
    
    @classmethod
    def build_single_tone_prompt(
        cls,
        dealership_name: str,
        city: str,
        tone: EmailTone,
        website: Optional[str] = None,
        owner_name: Optional[str] = None,
        dealership_type: DealershipType = DealershipType.USED_CAR,
        extra_context: Optional[str] = None
    ) -> str:
        """Build optimized prompt for single tone email generation."""
        
        owner_info = f"Owner: {owner_name}" if owner_name else "Owner: [Name from email]"
        website_info = website or "Not available"
        dealership_type_str = dealership_type.value.replace("_", " ").title()
        context = extra_context or "Standard automotive dealership"
        
        prompt = f"""Context: {dealership_name} in {city}
Website: {website_info}
{owner_info}
Business: {dealership_type_str} dealership
{context}

Generate {tone.value} tone email content:

1. SUBJECT: 6-8 words, personalized with owner name if available
2. ICEBREAKER: 2-3 sentences with specific dealership references
3. HOT_BUTTON: 1 sentence identifying key business challenge for {dealership_type_str} dealers

Format:
SUBJECT: [subject line]
ICEBREAKER: [icebreaker paragraph]
HOT_BUTTON: [business challenge]"""
        
        return prompt


class QualityScorer:
    """Content quality scoring system."""
    
    @staticmethod
    def score_subject_line(subject: str, owner_name: Optional[str] = None) -> float:
        """Score subject line quality (0-100)."""
        score = 0
        
        # Length check (6-10 words is optimal)
        word_count = len(subject.split())
        if 6 <= word_count <= 10:
            score += 25
        elif 4 <= word_count <= 12:
            score += 15
        else:
            score += 5
        
        # Personalization check
        if owner_name and owner_name.lower() in subject.lower():
            score += 25
        
        # Avoid spam words
        spam_words = ['free', 'urgent', 'act now', 'limited time', '!!!']
        spam_count = sum(1 for word in spam_words if word in subject.lower())
        score += max(0, 25 - spam_count * 10)
        
        # Professional tone check
        if not any(char in subject for char in ['!!!', 'FREE', 'URGENT']):
            score += 15
        
        # Business relevance
        business_words = ['dealership', 'sales', 'inventory', 'customers', 'marketing', 'growth']
        if any(word in subject.lower() for word in business_words):
            score += 10
        
        return min(100, score)
    
    @staticmethod
    def score_icebreaker(icebreaker: str, dealership_name: str, city: str) -> float:
        """Score icebreaker quality (0-100)."""
        score = 0
        
        # Length check (20-80 words is optimal)
        word_count = len(icebreaker.split())
        if 20 <= word_count <= 80:
            score += 25
        elif 15 <= word_count <= 100:
            score += 15
        else:
            score += 5
        
        # Personalization check
        mentions_dealership = dealership_name.lower() in icebreaker.lower()
        mentions_city = city.lower() in icebreaker.lower()
        
        if mentions_dealership and mentions_city:
            score += 30
        elif mentions_dealership or mentions_city:
            score += 15
        
        # Specificity check
        specific_words = ['noticed', 'researched', 'seen', 'reviewed', 'following']
        if any(word in icebreaker.lower() for word in specific_words):
            score += 20
        
        # Professional tone
        if not icebreaker.startswith('Hi ') and 'I hope this email finds you well' not in icebreaker:
            score += 15
        
        # Business focus
        business_terms = ['business', 'dealership', 'customers', 'sales', 'market', 'inventory']
        business_mentions = sum(1 for term in business_terms if term in icebreaker.lower())
        score += min(10, business_mentions * 3)
        
        return min(100, score)
    
    @staticmethod
    def score_hot_button(hot_button: str) -> float:
        """Score hot button topic quality (0-100)."""
        score = 0
        
        # Length check (10-30 words is optimal)
        word_count = len(hot_button.split())
        if 10 <= word_count <= 30:
            score += 30
        elif 5 <= word_count <= 40:
            score += 20
        else:
            score += 10
        
        # Business challenge focus
        challenge_words = [
            'increase', 'improve', 'optimize', 'boost', 'enhance', 'grow',
            'reduce', 'decrease', 'streamline', 'automate', 'efficiency',
            'customers', 'sales', 'revenue', 'profit', 'leads', 'conversion'
        ]
        challenge_mentions = sum(1 for word in challenge_words if word in hot_button.lower())
        score += min(30, challenge_mentions * 5)
        
        # Industry relevance
        industry_terms = [
            'inventory', 'financing', 'service', 'parts', 'warranty',
            'certification', 'manufacturer', 'allocation', 'marketing',
            'reputation', 'competitive', 'digital', 'online'
        ]
        industry_mentions = sum(1 for term in industry_terms if term in hot_button.lower())
        score += min(25, industry_mentions * 5)
        
        # Actionable language
        action_words = ['could', 'might', 'would', 'help', 'support', 'address', 'solve']
        if any(word in hot_button.lower() for word in action_words):
            score += 15
        
        return min(100, score)
    
    @classmethod
    def score_complete_email(
        cls,
        subject: str,
        icebreaker: str,
        hot_button: str,
        dealership_name: str,
        city: str,
        owner_name: Optional[str] = None
    ) -> Dict[str, float]:
        """Score complete email content."""
        return {
            'subject_score': cls.score_subject_line(subject, owner_name),
            'icebreaker_score': cls.score_icebreaker(icebreaker, dealership_name, city),
            'hot_button_score': cls.score_hot_button(hot_button),
            'overall_score': (
                cls.score_subject_line(subject, owner_name) * 0.3 +
                cls.score_icebreaker(icebreaker, dealership_name, city) * 0.5 +
                cls.score_hot_button(hot_button) * 0.2
            )
        }


# Pre-built templates for common scenarios
QUICK_TEMPLATES = {
    EmailTone.PROFESSIONAL: EmailTemplate(
        subject_template="{owner_name}: Strategic Growth for {dealership_name}",
        icebreaker_template="I've been analyzing successful dealerships in {city}, and {dealership_name}'s {unique_aspect} positions you well for the current market conditions.",
        hot_button_template="Many {dealership_type} dealers in your area are seeing 20-30% improvements in {improvement_area} with the right digital strategy.",
        tone=EmailTone.PROFESSIONAL
    ),
    
    EmailTone.FRIENDLY: EmailTemplate(
        subject_template="Hi {owner_name} - Growing {dealership_name} Together",
        icebreaker_template="Hi {owner_name}, I hope you're having a great week at {dealership_name}! I've been working with several {dealership_type} dealers in {city} and thought you might be interested in some trends I'm seeing.",
        hot_button_template="Most dealers I work with tell me that {common_challenge} is their biggest headache right now.",
        tone=EmailTone.FRIENDLY
    ),
    
    EmailTone.URGENT: EmailTemplate(
        subject_template="{owner_name}: {city} Market Opportunity for {dealership_name}",
        icebreaker_template="The {city} automotive market is shifting rapidly, and forward-thinking dealers like {dealership_name} have a unique window of opportunity right now.",
        hot_button_template="Dealers who don't address {urgent_challenge} in the next 90 days typically see a 15-25% drop in {metric_area}.",
        tone=EmailTone.URGENT
    )
}