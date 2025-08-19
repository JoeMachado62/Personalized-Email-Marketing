#!/usr/bin/env python3
"""
Intelligent Data Interpreter - AI-powered interpretation of extracted data.

This replaces the old pattern-based data_interpreter.py with an intelligent system
that understands context and generates high-quality personalization content.

Key improvements:
- Semantic understanding of extracted data
- Context-aware email generation
- Quality scoring for personalization elements
- Integration with LLM for enhanced interpretation (when available)
"""

import json
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
import hashlib

from .intelligent_extractor_v2 import PersonalizationIntelligence

logger = logging.getLogger(__name__)


@dataclass
class PersonalizedContent:
    """
    Structured personalized content ready for email campaigns.
    """
    # Email Components
    subject_lines: List[str] = field(default_factory=list)
    preview_texts: List[str] = field(default_factory=list)
    opening_lines: List[str] = field(default_factory=list)
    value_propositions: List[str] = field(default_factory=list)
    call_to_actions: List[str] = field(default_factory=list)
    
    # Personalization Elements
    pain_points_addressed: List[str] = field(default_factory=list)
    benefits_highlighted: List[str] = field(default_factory=list)
    social_proof_elements: List[str] = field(default_factory=list)
    urgency_factors: List[str] = field(default_factory=list)
    
    # Targeting Data
    best_time_to_send: str = ""
    personalization_score: float = 0.0
    confidence_level: str = ""
    
    # A/B Testing Variants
    variant_a: Dict[str, str] = field(default_factory=dict)
    variant_b: Dict[str, str] = field(default_factory=dict)
    
    # Metadata
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    interpretation_method: str = "intelligent_v2"


class IntelligentDataInterpreter:
    """
    Intelligent interpreter that transforms raw intelligence into personalized content.
    """
    
    def __init__(self, campaign_context: Optional[Dict] = None, use_llm: bool = False):
        """
        Initialize the interpreter.
        
        Args:
            campaign_context: Context about the campaign for better interpretation
            use_llm: Whether to use LLM for enhanced interpretation
        """
        self.campaign_context = campaign_context or {}
        self.use_llm = use_llm
        
        # Default campaign context
        self.default_context = {
            'tone': 'professional_friendly',
            'goal': 'schedule_meeting',
            'value_proposition': 'help_grow_business',
            'industry': 'general',
            'sender_name': 'Your Partner',
            'sender_company': 'Growth Solutions'
        }
        
        # Merge with provided context
        self.context = {**self.default_context, **self.campaign_context}
    
    async def interpret_with_llm(
        self,
        intelligence: PersonalizationIntelligence,
        use_llm: bool = True
    ) -> PersonalizedContent:
        """Generate truly personalized content using LLM with all extracted data."""
        
        if use_llm and intelligence.business_name:
            try:
                # Import the LLM service
                from .ai_enrichment import _call_language_model
                
                # Build rich context from all extracted data
                context_parts = []
                
                if intelligence.owner_name:
                    context_parts.append(f"Owner/Leader: {intelligence.owner_name} ({intelligence.owner_title or 'Owner'})")
                
                if intelligence.years_in_business:
                    context_parts.append(f"Established: {intelligence.years_in_business} years ago")
                
                if intelligence.recent_wins:
                    context_parts.append(f"Recent achievements: {', '.join(intelligence.recent_wins[:2])}")
                
                if intelligence.website_issues:
                    context_parts.append(f"Website issues: {', '.join(intelligence.website_issues[:2])}")
                
                if intelligence.missing_capabilities:
                    context_parts.append(f"Missing: {', '.join(intelligence.missing_capabilities[:2])}")
                
                if intelligence.community_involvement:
                    context_parts.append(f"Community: {', '.join(intelligence.community_involvement[:2])}")
                
                context = '\n'.join(context_parts)
                
                # Create rich prompt with all data
                prompt = f"""You are creating personalized outreach for a business owner.

BUSINESS INTELLIGENCE:
Name: {intelligence.business_name}
{context}

Create UNIQUE, HIGHLY PERSONALIZED content (not templates):

1. SUBJECT LINE: Creative, specific to THIS business (not generic)
2. OPENING LINE: Reference something specific about their business
3. VALUE PROPOSITION: How you can help with their specific situation

Be creative and specific. Avoid generic templates.

Format:
SUBJECT: [unique subject]
OPENING: [specific opening]
VALUE: [targeted value prop]"""
                
                # Call LLM
                response = await _call_language_model(prompt)
                
                # Parse response
                lines = response.split('\n')
                subject = ""
                opening = ""
                value = ""
                
                for line in lines:
                    if line.startswith("SUBJECT:"):
                        subject = line[8:].strip()
                    elif line.startswith("OPENING:"):
                        opening = line[8:].strip()
                    elif line.startswith("VALUE:"):
                        value = line[6:].strip()
                
                # Create PersonalizedContent with LLM output
                content = PersonalizedContent()
                if subject:
                    content.subject_lines = [subject]
                if opening:
                    content.opening_lines = [opening]
                if value:
                    content.value_propositions = [value]
                
                # Add other fields
                content.pain_points_addressed = intelligence.pain_points_addressed[:3]
                content.personalization_score = 0.9  # High score for LLM content
                content.confidence_level = "high"
                
                return content
                
            except Exception as e:
                logger.warning(f"LLM generation failed, falling back to templates: {e}")
        
        # Fall back to template-based generation
        return self.interpret(intelligence)
    
    def interpret(
        self,
        intelligence: PersonalizationIntelligence,
        additional_data: Optional[Dict] = None
    ) -> PersonalizedContent:
        """
        Main interpretation method that generates personalized content.
        
        Args:
            intelligence: Extracted intelligence from web scraping
            additional_data: Any additional data to consider
            
        Returns:
            PersonalizedContent ready for email campaigns
        """
        content = PersonalizedContent()
        
        try:
            # Step 1: Analyze the quality of intelligence
            quality_score = self._assess_intelligence_quality(intelligence)
            
            # Step 2: Generate subject lines based on intelligence
            content.subject_lines = self._generate_subject_lines(intelligence)
            
            # Step 3: Generate preview texts
            content.preview_texts = self._generate_preview_texts(intelligence)
            
            # Step 4: Generate opening lines
            content.opening_lines = self._generate_opening_lines(intelligence)
            
            # Step 5: Generate value propositions
            content.value_propositions = self._generate_value_propositions(intelligence)
            
            # Step 6: Generate CTAs
            content.call_to_actions = self._generate_ctas(intelligence)
            
            # Step 7: Identify pain points to address
            content.pain_points_addressed = self._identify_pain_points_to_address(intelligence)
            
            # Step 8: Highlight benefits
            content.benefits_highlighted = self._highlight_benefits(intelligence)
            
            # Step 9: Add social proof
            content.social_proof_elements = self._create_social_proof(intelligence)
            
            # Step 10: Create urgency
            content.urgency_factors = self._create_urgency_factors(intelligence)
            
            # Step 11: Determine best send time
            content.best_time_to_send = self._determine_best_send_time(intelligence)
            
            # Step 12: Create A/B variants
            content.variant_a, content.variant_b = self._create_ab_variants(content, intelligence)
            
            # Step 13: Calculate personalization score
            content.personalization_score = self._calculate_personalization_score(content, intelligence)
            content.confidence_level = self._get_confidence_level(content.personalization_score)
            
        except Exception as e:
            logger.error(f"Interpretation failed: {e}")
            content = self._create_fallback_content(intelligence)
        
        return content
    
    def _assess_intelligence_quality(self, intelligence: PersonalizationIntelligence) -> float:
        """Assess the quality of extracted intelligence."""
        score = 0.0
        
        # Check for essential data
        if intelligence.business_name:
            score += 0.1
        if intelligence.owner_name:
            score += 0.2
        if intelligence.owner_email or intelligence.owner_phone:
            score += 0.1
        
        # Check for personalization goldmines
        if intelligence.recent_announcements:
            score += 0.15
        if intelligence.recent_wins:
            score += 0.15
        if intelligence.website_issues or intelligence.missing_capabilities:
            score += 0.1
        if intelligence.community_involvement:
            score += 0.1
        if intelligence.customer_success_stories:
            score += 0.1
        
        return min(score, 1.0)
    
    def _generate_subject_lines(self, intelligence: PersonalizationIntelligence) -> List[str]:
        """Generate personalized subject lines."""
        subjects = []
        
        # Based on recent achievements
        if intelligence.recent_wins:
            win = intelligence.recent_wins[0]
            subjects.append(f"Congrats on {self._truncate(win, 30)}! 🎉")
            subjects.append(f"Saw your {self._truncate(win, 25)} - impressive!")
        
        # Based on recent announcements
        if intelligence.recent_announcements:
            announcement = intelligence.recent_announcements[0]
            subjects.append(f"Re: {self._truncate(announcement.get('title', ''), 35)}")
            subjects.append(f"About your {self._truncate(announcement.get('title', ''), 30)}")
        
        # Based on pain points
        if intelligence.website_issues:
            issue = intelligence.website_issues[0]
            subjects.append(f"Quick fix for your {issue.lower()}")
            subjects.append(f"Noticed something about {intelligence.business_name}'s website")
        
        # Based on missing capabilities
        if intelligence.missing_capabilities:
            capability = intelligence.missing_capabilities[0]
            subjects.append(f"How {intelligence.business_name} can add {capability.lower()}")
        
        # Personalized with owner name
        if intelligence.owner_name:
            first_name = intelligence.owner_name.split()[0] if intelligence.owner_name else ""
            if first_name:
                subjects.append(f"{first_name}, quick question about {intelligence.business_name}")
                subjects.append(f"Ideas for {first_name} at {intelligence.business_name}")
        
        # Community-based
        if intelligence.community_involvement:
            subjects.append(f"Love what {intelligence.business_name} does for the community")
        
        # Time-sensitive
        if intelligence.upcoming_events:
            subjects.append(f"Before your {intelligence.upcoming_events[0].get('title', 'event')}")
        
        # Add subjects based on years in business (high value!)
        if intelligence.years_in_business:
            years = intelligence.years_in_business
            if years >= 25:
                subjects.append(f"Celebrating {years} years - ready for digital growth?")
                subjects.append(f"{years} years strong! Let's modernize together")
            elif years >= 10:
                subjects.append(f"{years} years of success - time to expand online?")
            elif years >= 5:
                subjects.append(f"Congrats on {years} years - let's talk growth")
        
        # Fallback subjects - but make them better
        if not subjects:
            # Try to use ANY available data
            if intelligence.owner_name and len(intelligence.owner_name.split()) >= 2:
                first_name = intelligence.owner_name.split()[0]
                subjects.append(f"{first_name}, quick question about {intelligence.business_name}")
            elif intelligence.years_in_business:
                subjects.append(f"After {intelligence.years_in_business} years, ready for what's next?")
            else:
                subjects.append(f"Quick question for {intelligence.business_name}")
            
            subjects.append(f"Idea to help {intelligence.business_name} grow")
            subjects.append(f"{intelligence.business_name} - 5 minute proposal")
        
        # Limit and deduplicate
        return list(dict.fromkeys(subjects))[:5]
    
    def _generate_preview_texts(self, intelligence: PersonalizationIntelligence) -> List[str]:
        """Generate preview texts for emails."""
        previews = []
        
        if intelligence.recent_wins:
            previews.append(f"Just saw your {self._truncate(intelligence.recent_wins[0], 40)}...")
        
        if intelligence.unique_value_props:
            previews.append(f"Your {self._truncate(intelligence.unique_value_props[0], 35)} caught my attention...")
        
        if intelligence.pain_points_addressed:
            previews.append(f"I can help with {self._truncate(intelligence.pain_points_addressed[0], 35)}...")
        
        if intelligence.community_involvement:
            previews.append(f"Your work with {self._truncate(intelligence.community_involvement[0], 30)} is inspiring...")
        
        # Fallbacks
        if not previews:
            previews = [
                "I have an idea that could help your business...",
                "Quick thought on growing your customer base...",
                "Noticed something that might interest you..."
            ]
        
        return previews[:3]
    
    def _generate_opening_lines(self, intelligence: PersonalizationIntelligence) -> List[str]:
        """Generate personalized opening lines."""
        openings = []
        
        # Congratulatory openings
        if intelligence.recent_wins:
            openings.append(f"First off, congratulations on {intelligence.recent_wins[0]}! That's a fantastic achievement.")
        
        if intelligence.recent_announcements:
            announcement = intelligence.recent_announcements[0]
            openings.append(f"I just read about {announcement.get('title', 'your recent announcement')} - exciting news for {intelligence.business_name}!")
        
        # Value-based openings
        if intelligence.community_involvement:
            openings.append(f"I really admire {intelligence.business_name}'s commitment to {intelligence.community_involvement[0]}.")
        
        if intelligence.company_values:
            openings.append(f"Your focus on {intelligence.company_values[0]} really resonates with me.")
        
        # Problem-solving openings
        if intelligence.website_issues:
            openings.append(f"I noticed your website {intelligence.website_issues[0].lower()}, and I might have a solution that could help.")
        
        if intelligence.missing_capabilities:
            openings.append(f"I see {intelligence.business_name} doesn't currently have {intelligence.missing_capabilities[0].lower()} - this could be a game-changer for your business.")
        
        # Social proof openings
        if intelligence.customer_success_stories:
            openings.append(f"Your customer's testimonial about '{self._truncate(intelligence.customer_success_stories[0].get('text', ''), 50)}' really stood out to me.")
        
        # Personal connection openings
        if intelligence.owner_name:
            first_name = intelligence.owner_name.split()[0] if intelligence.owner_name else ""
            if first_name:
                openings.append(f"Hi {first_name}, I've been following {intelligence.business_name}'s journey and I'm impressed by what you've built.")
        
        # Add opening based on years in business (VERY POWERFUL)
        if intelligence.years_in_business:
            years = intelligence.years_in_business
            if years >= 40:
                openings.insert(0, f"Wow - {years} years in business! That's incredibly rare and impressive.")
            elif years >= 25:
                openings.insert(0, f"After {years} successful years, you've clearly mastered your market.")
            elif years >= 10:
                openings.insert(0, f"Building a business that thrives for {years} years is no small feat.")
        
        # Fallback openings - but personalized if possible
        if not openings:
            if intelligence.years_in_business:
                openings.append(f"After {intelligence.years_in_business} years in business, I thought this might interest you.")
            else:
                openings.append(f"I came across {intelligence.business_name} and was impressed by your business.")
            
            openings.append(f"I've been researching successful Florida dealerships and {intelligence.business_name} stood out.")
            openings.append(f"I help dealerships like {intelligence.business_name} modernize their digital presence.")
        
        return openings[:5]
    
    def _generate_value_propositions(self, intelligence: PersonalizationIntelligence) -> List[str]:
        """Generate value propositions based on intelligence."""
        props = []
        
        # Address specific pain points
        if intelligence.website_issues:
            for issue in intelligence.website_issues[:2]:
                props.append(f"I can help modernize your web presence and fix the {issue.lower()} issue")
        
        if intelligence.missing_capabilities:
            for capability in intelligence.missing_capabilities[:2]:
                props.append(f"I'll implement {capability.lower()} to streamline your operations and boost revenue")
        
        # Competitive advantages
        if intelligence.competitor_advantages:
            props.append("I'll help you match and exceed what your competitors are doing")
        
        # Growth opportunities
        if intelligence.market_opportunities:
            props.append(f"Let's capitalize on {intelligence.market_opportunities[0]}")
        
        # Based on their values
        if intelligence.company_values:
            props.append(f"My solution aligns perfectly with your commitment to {intelligence.company_values[0]}")
        
        # Based on their success
        if intelligence.recent_wins:
            props.append(f"Let's build on your recent success with {intelligence.recent_wins[0]}")
        
        # Based on years in business
        if intelligence.years_in_business:
            years = intelligence.years_in_business
            if years >= 20:
                props.append(f"After {years} years, you deserve modern tools that match your expertise")
                props.append(f"Let's ensure your next {years} years are even more successful")
            elif years >= 10:
                props.append(f"I'll help you leverage your {years} years of reputation online")
        
        # Pain-point specific
        if intelligence.pain_points_addressed:
            for pain in intelligence.pain_points_addressed[:2]:
                props.append(f"I specialize in {pain.lower()} for dealerships like yours")
        
        # Generic but better - only if needed
        if len(props) < 3:
            if intelligence.years_in_business and intelligence.years_in_business >= 10:
                props.append(f"Businesses with your {intelligence.years_in_business}-year track record see 40% growth with our system")
            else:
                props.append(f"I've helped 50+ Florida dealerships increase revenue by 30%")
            
            props.append(f"My proven system can bring you 20+ qualified leads per month")
            props.append(f"I'll modernize your digital presence while respecting what's made you successful")
        
        return props[:5]
    
    def _generate_ctas(self, intelligence: PersonalizationIntelligence) -> List[str]:
        """Generate call-to-action options."""
        ctas = []
        
        # Time-sensitive CTAs
        if intelligence.upcoming_events:
            ctas.append(f"Can we chat before your {intelligence.upcoming_events[0].get('title', 'event')}?")
        
        # Casual CTAs
        ctas.extend([
            "Would you be open to a quick 15-minute call this week?",
            "Can I send you a brief proposal with 3 ideas?",
            "Are you available for a coffee chat on Thursday or Friday?",
            "Mind if I share a 2-minute video with some ideas for you?"
        ])
        
        # Direct CTAs
        if intelligence.owner_name:
            first_name = intelligence.owner_name.split()[0] if intelligence.owner_name else ""
            if first_name:
                ctas.append(f"{first_name}, when would be a good time to discuss this?")
        
        # Value-focused CTAs
        ctas.extend([
            "Want to see how this would work specifically for your business?",
            "Interested in a free analysis of your current situation?",
            "Can I show you what we did for a similar business?"
        ])
        
        return ctas[:5]
    
    def _identify_pain_points_to_address(self, intelligence: PersonalizationIntelligence) -> List[str]:
        """Identify which pain points to address in the email."""
        pain_points = []
        
        # Direct pain points
        pain_points.extend(intelligence.website_issues[:2])
        pain_points.extend(intelligence.missing_capabilities[:2])
        
        # Inferred pain points
        if not intelligence.recent_announcements and not intelligence.recent_posts:
            pain_points.append("Lack of recent online activity may be affecting visibility")
        
        if not intelligence.customer_success_stories:
            pain_points.append("Missing social proof on website")
        
        if intelligence.competitor_advantages:
            pain_points.append("Competitors have advantages that need to be addressed")
        
        return pain_points[:5]
    
    def _highlight_benefits(self, intelligence: PersonalizationIntelligence) -> List[str]:
        """Highlight benefits relevant to the business."""
        benefits = []
        
        # Based on their industry/services
        if intelligence.primary_services:
            benefits.append(f"Attract more customers looking for {intelligence.primary_services[0]}")
        
        # Based on their values
        if intelligence.company_values:
            benefits.append(f"Strengthen your reputation for {intelligence.company_values[0]}")
        
        # Based on their challenges
        if intelligence.website_issues:
            benefits.append("Modernize your online presence to match your quality service")
        
        if intelligence.missing_capabilities:
            benefits.append("Automate customer interactions to save time and increase satisfaction")
        
        # Generic benefits
        benefits.extend([
            "Increase revenue without increasing workload",
            "Build stronger relationships with your customers",
            "Stand out from your competition",
            "Get found by more potential customers online"
        ])
        
        return benefits[:5]
    
    def _create_social_proof(self, intelligence: PersonalizationIntelligence) -> List[str]:
        """Create social proof elements."""
        proof = []
        
        # Use their own testimonials as reference
        if intelligence.customer_success_stories:
            proof.append(f"Just like your customer said: '{self._truncate(intelligence.customer_success_stories[0].get('text', ''), 50)}'")
        
        # Reference their achievements
        if intelligence.recent_wins:
            proof.append(f"Building on achievements like {intelligence.recent_wins[0]}")
        
        if intelligence.certifications:
            proof.append(f"Perfect for a {intelligence.certifications[0]} certified business")
        
        # Generic social proof
        proof.extend([
            "Join 500+ businesses who've transformed their online presence",
            "Trusted by leading companies in your industry",
            "Proven results with 95% client satisfaction rate"
        ])
        
        return proof[:3]
    
    def _create_urgency_factors(self, intelligence: PersonalizationIntelligence) -> List[str]:
        """Create urgency factors for the email."""
        urgency = []
        
        # Time-based urgency
        if intelligence.upcoming_events:
            urgency.append(f"Get this implemented before your {intelligence.upcoming_events[0].get('title', 'event')}")
        
        if intelligence.seasonal_promotions:
            urgency.append("Perfect timing with your seasonal promotion")
        
        # Competition-based urgency
        if intelligence.competitor_advantages:
            urgency.append("Your competitors are already ahead in this area")
        
        # Market-based urgency
        month = datetime.now().strftime("%B")
        urgency.extend([
            f"Limited {month} pricing available",
            "Only taking on 3 new clients this month",
            "Special offer expires this Friday"
        ])
        
        return urgency[:3]
    
    def _determine_best_send_time(self, intelligence: PersonalizationIntelligence) -> str:
        """Determine the best time to send the email."""
        # Based on their activity patterns
        if intelligence.latest_social_posts:
            # Analyze posting times (simplified)
            return "Tuesday-Thursday, 10am-12pm (based on their posting pattern)"
        
        # Based on industry standards
        if 'restaurant' in str(intelligence.primary_services).lower():
            return "Tuesday-Thursday, 2pm-4pm (avoid rush hours)"
        elif 'auto' in intelligence.business_name.lower():
            return "Wednesday-Friday, 9am-11am"
        else:
            return "Tuesday-Thursday, 10am-11am or 2pm-3pm"
    
    def _create_ab_variants(
        self,
        content: PersonalizedContent,
        intelligence: PersonalizationIntelligence
    ) -> Tuple[Dict[str, str], Dict[str, str]]:
        """Create A/B testing variants."""
        variant_a = {
            'subject': content.subject_lines[0] if content.subject_lines else "Quick question",
            'opening': content.opening_lines[0] if content.opening_lines else "Hi there,",
            'cta': content.call_to_actions[0] if content.call_to_actions else "Let's chat?",
            'tone': 'professional'
        }
        
        variant_b = {
            'subject': content.subject_lines[1] if len(content.subject_lines) > 1 else f"Idea for {intelligence.business_name}",
            'opening': content.opening_lines[1] if len(content.opening_lines) > 1 else f"Hey {intelligence.owner_name.split()[0] if intelligence.owner_name else 'there'},",
            'cta': content.call_to_actions[1] if len(content.call_to_actions) > 1 else "Want to learn more?",
            'tone': 'casual'
        }
        
        return variant_a, variant_b
    
    def _calculate_personalization_score(
        self,
        content: PersonalizedContent,
        intelligence: PersonalizationIntelligence
    ) -> float:
        """Calculate how well personalized the content is."""
        score = 0.0
        
        # Check content quality
        if len(content.subject_lines) >= 3:
            score += 0.15
        if len(content.opening_lines) >= 3:
            score += 0.15
        if content.pain_points_addressed:
            score += 0.2
        if content.social_proof_elements:
            score += 0.1
        
        # Check intelligence quality
        if intelligence.owner_name:
            score += 0.15
        if intelligence.recent_announcements or intelligence.recent_wins:
            score += 0.15
        if intelligence.extraction_confidence > 0.7:
            score += 0.1
        
        return min(score, 1.0)
    
    def _get_confidence_level(self, score: float) -> str:
        """Get confidence level description."""
        if score >= 0.8:
            return "High - Excellent personalization"
        elif score >= 0.6:
            return "Good - Well personalized"
        elif score >= 0.4:
            return "Medium - Some personalization"
        else:
            return "Low - Limited personalization"
    
    def _create_fallback_content(self, intelligence: PersonalizationIntelligence) -> PersonalizedContent:
        """Create fallback content when interpretation fails."""
        content = PersonalizedContent()
        
        content.subject_lines = [
            f"Quick question for {intelligence.business_name}",
            f"Idea to help {intelligence.business_name} grow"
        ]
        
        content.opening_lines = [
            f"I came across {intelligence.business_name} and thought I might be able to help.",
            f"I noticed {intelligence.business_name} online and have an idea for you."
        ]
        
        content.value_propositions = [
            "I can help you attract more customers",
            "Let me show you how to grow your business"
        ]
        
        content.call_to_actions = [
            "Would you be open to a quick call?",
            "Can I send you more information?"
        ]
        
        content.personalization_score = 0.2
        content.confidence_level = "Fallback - Minimal personalization"
        
        return content
    
    def _truncate(self, text: str, max_length: int) -> str:
        """Truncate text to maximum length."""
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."
    
    def generate_full_email(
        self,
        content: PersonalizedContent,
        intelligence: PersonalizationIntelligence,
        variant: str = 'a'
    ) -> str:
        """
        Generate a complete email from the personalized content.
        
        Args:
            content: Personalized content elements
            intelligence: Business intelligence
            variant: Which variant to use ('a' or 'b')
            
        Returns:
            Complete email text
        """
        v = content.variant_a if variant == 'a' else content.variant_b
        
        # Select best elements
        opening = v.get('opening', content.opening_lines[0] if content.opening_lines else "Hi there,")
        value_prop = content.value_propositions[0] if content.value_propositions else ""
        pain_point = content.pain_points_addressed[0] if content.pain_points_addressed else ""
        benefit = content.benefits_highlighted[0] if content.benefits_highlighted else ""
        social_proof = content.social_proof_elements[0] if content.social_proof_elements else ""
        cta = v.get('cta', content.call_to_actions[0] if content.call_to_actions else "Let's connect?")
        
        # Build email
        email_parts = [opening]
        
        if pain_point:
            email_parts.append(f"\nI noticed {pain_point.lower()}. {value_prop}")
        else:
            email_parts.append(f"\n{value_prop}")
        
        if benefit:
            email_parts.append(f"\nThis would help you {benefit.lower()}.")
        
        if social_proof:
            email_parts.append(f"\n{social_proof}")
        
        email_parts.append(f"\n{cta}")
        
        email_parts.append(f"\nBest regards,\n{self.context.get('sender_name', 'Your Partner')}")
        email_parts.append(f"{self.context.get('sender_company', 'Growth Solutions')}")
        
        return "\n".join(email_parts)


# Test function
def test_interpreter():
    """Test the intelligent data interpreter."""
    
    # Create sample intelligence
    intelligence = PersonalizationIntelligence(
        business_name="Smith Auto Dealership",
        owner_name="John Smith",
        owner_title="President",
        recent_announcements=[
            {"date": "November 2024", "title": "Grand Opening of New Service Center"}
        ],
        recent_wins=["2024 Dealer of the Year Award"],
        website_issues=["Website not mobile-optimized"],
        missing_capabilities=["No online appointment booking"],
        customer_success_stories=[
            {"text": "Best service I've ever received!", "author": "Sarah J."}
        ],
        community_involvement=["Local Little League sponsorship"],
        primary_services=["New Car Sales", "Auto Service", "Financing"],
        extraction_confidence=0.85
    )
    
    # Create interpreter with campaign context
    campaign_context = {
        'tone': 'professional_friendly',
        'goal': 'schedule_meeting',
        'sender_name': 'Mike Johnson',
        'sender_company': 'Digital Growth Partners',
        'industry': 'automotive'
    }
    
    interpreter = IntelligentDataInterpreter(campaign_context)
    
    # Generate personalized content
    content = interpreter.interpret(intelligence)
    
    print("\n" + "="*60)
    print("PERSONALIZED CONTENT GENERATED")
    print("="*60)
    
    print("\n📧 Subject Lines:")
    for i, subject in enumerate(content.subject_lines[:3], 1):
        print(f"  {i}. {subject}")
    
    print("\n👀 Preview Texts:")
    for i, preview in enumerate(content.preview_texts[:2], 1):
        print(f"  {i}. {preview}")
    
    print("\n🎯 Opening Lines:")
    for i, opening in enumerate(content.opening_lines[:2], 1):
        print(f"  {i}. {opening}")
    
    print("\n💡 Value Propositions:")
    for i, prop in enumerate(content.value_propositions[:2], 1):
        print(f"  {i}. {prop}")
    
    print("\n⏰ Best Send Time:")
    print(f"  {content.best_time_to_send}")
    
    print("\n📊 Quality Metrics:")
    print(f"  Personalization Score: {content.personalization_score:.1%}")
    print(f"  Confidence: {content.confidence_level}")
    
    print("\n" + "="*60)
    print("COMPLETE EMAIL (Variant A)")
    print("="*60)
    email = interpreter.generate_full_email(content, intelligence, 'a')
    print(email)
    
    return content


if __name__ == "__main__":
    test_interpreter()