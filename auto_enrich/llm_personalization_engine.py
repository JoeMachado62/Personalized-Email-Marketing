#!/usr/bin/env python3
"""
LLM-Powered Personalization Engine

This module takes the rich PersonalizationIntelligence data structure
and uses it to generate TRULY personalized content via LLM, not templates.

The whole point of extracting detailed business intelligence is to feed it
to an LLM for creative, unique personalization - not to plug it into templates!
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Any
from dataclasses import asdict

from .intelligent_extractor_v2 import PersonalizationIntelligence
from .intelligent_data_interpreter import PersonalizedContent
from .config import LLM_API_KEY, LLM_MODEL_NAME
from .ai_enrichment import _call_language_model

logger = logging.getLogger(__name__)


class LLMPersonalizationEngine:
    """
    Generates truly personalized content using LLM with all extracted intelligence.
    """
    
    def __init__(self, campaign_context: Optional[Dict] = None):
        """
        Initialize the LLM personalization engine.
        
        Args:
            campaign_context: Campaign-specific context for personalization
        """
        self.campaign_context = campaign_context or {}
        
        if not LLM_API_KEY:
            logger.warning("No LLM_API_KEY configured - personalization will be limited")
    
    async def generate_personalized_content(
        self,
        intelligence: PersonalizationIntelligence
    ) -> PersonalizedContent:
        """
        Generate truly personalized content using LLM with ALL extracted data.
        
        This is the RIGHT way to do it - feed all the intelligence to the LLM
        and let it create unique, creative content for each business.
        
        Args:
            intelligence: Complete business intelligence extracted from web
            
        Returns:
            PersonalizedContent with LLM-generated unique content
        """
        
        if not LLM_API_KEY:
            logger.error("Cannot generate LLM content without API key")
            return self._fallback_content(intelligence)
        
        try:
            # Build comprehensive context from ALL extracted data
            context = self._build_rich_context(intelligence)
            
            # Create detailed prompt with all intelligence
            prompt = self._create_comprehensive_prompt(intelligence, context)
            
            # Call LLM for creative personalization
            logger.info(f"Calling LLM for {intelligence.business_name}...")
            response = await _call_language_model(prompt)
            logger.debug(f"LLM Response: {response[:500]}...")  # Log first 500 chars
            
            # Parse LLM response into PersonalizedContent
            content = self._parse_llm_response(response, intelligence)
            
            # Add confidence and quality scores
            content.personalization_score = self._calculate_personalization_score(intelligence)
            content.confidence_level = "high" if content.personalization_score > 0.7 else "medium"
            
            logger.info(f"Generated LLM personalization for {intelligence.business_name} (score: {content.personalization_score:.2f})")
            
            return content
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return self._fallback_content(intelligence)
    
    def _build_rich_context(self, intelligence: PersonalizationIntelligence) -> str:
        """
        Build comprehensive context string from all extracted intelligence.
        This is the key - we're using EVERYTHING we extracted!
        """
        
        sections = []
        
        # Business basics
        if intelligence.business_name:
            sections.append(f"Business: {intelligence.business_name}")
        
        if intelligence.website_url:
            sections.append(f"Website: {intelligence.website_url}")
        
        # Leadership and ownership
        if intelligence.owner_name:
            owner_info = f"Owner/Leader: {intelligence.owner_name}"
            if intelligence.owner_title:
                owner_info += f" ({intelligence.owner_title})"
            sections.append(owner_info)
            
            if intelligence.owner_email:
                sections.append(f"Owner Email: {intelligence.owner_email}")
            if intelligence.owner_phone:
                sections.append(f"Owner Phone: {intelligence.owner_phone}")
        
        # Business history and credibility
        if intelligence.years_in_business:
            sections.append(f"Years in Business: {intelligence.years_in_business}")
            if intelligence.years_in_business >= 25:
                sections.append("Notable: Quarter-century or more of operation")
        
        # Recent activity and achievements
        if intelligence.recent_announcements:
            announcements = [f"- {ann.get('date', 'Recent')}: {ann.get('title', 'Announcement')}" 
                           for ann in intelligence.recent_announcements[:3]]
            sections.append("Recent Announcements:\n" + "\n".join(announcements))
        
        if intelligence.recent_wins:
            wins = [f"- {win}" for win in intelligence.recent_wins[:3]]
            sections.append("Recent Achievements:\n" + "\n".join(wins))
        
        # Pain points and opportunities
        if intelligence.website_issues:
            issues = [f"- {issue}" for issue in intelligence.website_issues[:3]]
            sections.append("Website Issues Identified:\n" + "\n".join(issues))
        
        if intelligence.missing_capabilities:
            missing = [f"- {cap}" for cap in intelligence.missing_capabilities[:3]]
            sections.append("Missing Capabilities:\n" + "\n".join(missing))
        
        if intelligence.pain_points_addressed:
            pain_points = [f"- {pp}" for pp in intelligence.pain_points_addressed[:3]]
            sections.append("Pain Points We Can Address:\n" + "\n".join(pain_points))
        
        # Social proof and community
        if intelligence.customer_success_stories:
            sections.append(f"Has {len(intelligence.customer_success_stories)} positive customer testimonials")
        
        if intelligence.ratings_summary:
            rating = intelligence.ratings_summary.get('average', 0)
            count = intelligence.ratings_summary.get('count', 0)
            if rating > 0:
                sections.append(f"Customer Rating: {rating}/5 ({count} reviews)")
        
        if intelligence.community_involvement:
            community = [f"- {inv}" for inv in intelligence.community_involvement[:2]]
            sections.append("Community Involvement:\n" + "\n".join(community))
        
        # Business details
        if intelligence.primary_services:
            services = [f"- {svc}" for svc in intelligence.primary_services[:5]]
            sections.append("Primary Services:\n" + "\n".join(services))
        
        if intelligence.company_values:
            values = [f"- {val}" for val in intelligence.company_values[:3]]
            sections.append("Company Values:\n" + "\n".join(values))
        
        if intelligence.certifications:
            certs = [f"- {cert}" for cert in intelligence.certifications[:3]]
            sections.append("Certifications/Status:\n" + "\n".join(certs))
        
        # Social media presence
        if intelligence.social_media_profiles:
            social = [f"- {platform}: Active" for platform in intelligence.social_media_profiles.keys()]
            sections.append("Social Media Presence:\n" + "\n".join(social))
        
        # Market opportunities
        if intelligence.market_opportunities:
            opps = [f"- {opp}" for opp in intelligence.market_opportunities[:2]]
            sections.append("Market Opportunities:\n" + "\n".join(opps))
        
        # Data quality indicators
        sections.append(f"Data Sources Analyzed: {len(intelligence.sources_analyzed)}")
        sections.append(f"Data Freshness: {intelligence.data_freshness}")
        sections.append(f"Extraction Confidence: {intelligence.extraction_confidence:.1%}")
        
        return "\n\n".join(sections)
    
    def _create_comprehensive_prompt(
        self,
        intelligence: PersonalizationIntelligence,
        context: str
    ) -> str:
        """
        Create a detailed prompt that gives the LLM all the context it needs
        to generate truly personalized, creative content.
        """
        
        # Campaign context
        campaign_info = ""
        if self.campaign_context:
            campaign_info = f"""
CAMPAIGN CONTEXT:
- Goal: {self.campaign_context.get('goal', 'Generate interest and schedule meeting')}
- Value Proposition: {self.campaign_context.get('value_proposition', 'Digital transformation services')}
- Sender: {self.campaign_context.get('sender_name', 'Digital Marketing Partner')}
- Industry Focus: {self.campaign_context.get('industry', 'Automotive dealerships')}
"""
        
        prompt = f"""You are an expert at creating highly personalized business outreach that gets responses.

{campaign_info}

EXTRACTED BUSINESS INTELLIGENCE:
{context}

YOUR TASK:
Create UNIQUE, HIGHLY PERSONALIZED outreach content for this specific business.
Use the intelligence above to craft messages that show deep understanding of their business.

REQUIREMENTS:
1. Reference specific details from the intelligence (years in business, achievements, pain points, etc.)
2. Be creative and avoid generic templates
3. Show that you've researched their business
4. Address their specific situation and needs
5. Stand out from typical marketing emails

GENERATE:

1. EMAIL SUBJECT LINES (3 variations):
   - Each should be unique and reference something specific about their business
   - Use different hooks: achievement, pain point, opportunity, etc.
   - Keep under 60 characters
   - Make them intriguing and personal

2. EMAIL OPENING LINES (3 variations):
   - Reference specific intelligence about their business
   - Show genuine interest/admiration for something they've done
   - Create immediate connection
   - Avoid generic greetings

3. VALUE PROPOSITIONS (3 variations):
   - Directly address their specific pain points or opportunities
   - Explain how you can help with their unique situation
   - Be specific about the value you bring to THEIR business
   - Reference their industry, size, or specific challenges

4. PERSONALIZED ICE BREAKERS (2 variations):
   - Something unique about their business that caught your attention
   - Could reference community involvement, achievements, or values

5. HOT BUTTON TOPICS (2 variations):
   - Specific business challenges they likely face
   - Based on the intelligence gathered

6. CALL TO ACTIONS (2 variations):
   - Specific and relevant to their situation
   - Low commitment but high value

Provide your response in the following format (one item per line, no JSON):

SUBJECT_1: [First subject line referencing their specific business]
SUBJECT_2: [Second subject line with different angle]
SUBJECT_3: [Third subject line]

OPENING_1: [First opening line mentioning specific details]
OPENING_2: [Second opening line]
OPENING_3: [Third opening line]

VALUE_1: [First value proposition addressing their pain points]
VALUE_2: [Second value proposition]
VALUE_3: [Third value proposition]

ICEBREAKER_1: [First ice breaker about their business]
ICEBREAKER_2: [Second ice breaker]

HOTBUTTON_1: [First business challenge]
HOTBUTTON_2: [Second business challenge]

CTA_1: [First call to action]
CTA_2: [Second call to action]"""
        
        return prompt
    
    def _parse_llm_response(
        self,
        response: str,
        intelligence: PersonalizationIntelligence
    ) -> PersonalizedContent:
        """
        Parse the LLM's JSON response into PersonalizedContent.
        """
        
        content = PersonalizedContent()
        
        try:
            # Try to parse as JSON
            if "```json" in response:
                # Extract JSON from markdown code block
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            else:
                # Try to find JSON object in response
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
            
            data = json.loads(json_str)
            
            # Extract all the personalized content
            content.subject_lines = data.get("subject_lines", [])[:5]
            content.opening_lines = data.get("opening_lines", [])[:5]
            content.value_propositions = data.get("value_propositions", [])[:5]
            content.ice_breakers = data.get("ice_breakers", [])[:3]
            content.hot_buttons = data.get("hot_buttons", [])[:3]
            content.call_to_actions = data.get("call_to_actions", [])[:5]
            
            # Add preview texts (can be generated from opening lines)
            content.preview_texts = [
                opening[:100] + "..." if len(opening) > 100 else opening
                for opening in content.opening_lines[:3]
            ]
            
            # Add pain points from intelligence
            content.pain_points_addressed = intelligence.pain_points_addressed[:5]
            
            # Store personalization notes if provided
            if "personalization_notes" in data:
                content.ice_breakers.append(f"Strategy: {data['personalization_notes']}")
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse LLM JSON response, falling back to text parsing: {e}")
            
            # Fallback: Parse as text
            lines = response.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Try to extract content from various formats
                if 'subject' in line.lower() and ':' in line:
                    subject = line.split(':', 1)[1].strip().strip('"')
                    if subject:
                        content.subject_lines.append(subject)
                
                elif 'opening' in line.lower() and ':' in line:
                    opening = line.split(':', 1)[1].strip().strip('"')
                    if opening:
                        content.opening_lines.append(opening)
                
                elif 'value' in line.lower() and ':' in line:
                    value = line.split(':', 1)[1].strip().strip('"')
                    if value:
                        content.value_propositions.append(value)
        
        # Ensure we have at least some content
        if not content.subject_lines:
            content.subject_lines = [f"Important opportunity for {intelligence.business_name}"]
        
        if not content.opening_lines:
            content.opening_lines = [f"I've been researching {intelligence.business_name} and I'm impressed."]
        
        if not content.value_propositions:
            content.value_propositions = ["I can help modernize your digital presence."]
        
        return content
    
    def _calculate_personalization_score(self, intelligence: PersonalizationIntelligence) -> float:
        """
        Calculate how personalized the content can be based on available data.
        """
        
        score = 0.0
        max_score = 0.0
        
        # Score based on data availability
        scoring_factors = [
            (intelligence.owner_name, 0.15),
            (intelligence.years_in_business, 0.15),
            (len(intelligence.recent_wins) > 0, 0.10),
            (len(intelligence.recent_announcements) > 0, 0.10),
            (len(intelligence.website_issues) > 0, 0.10),
            (len(intelligence.missing_capabilities) > 0, 0.10),
            (len(intelligence.community_involvement) > 0, 0.05),
            (len(intelligence.customer_success_stories) > 0, 0.05),
            (intelligence.ratings_summary, 0.05),
            (len(intelligence.company_values) > 0, 0.05),
            (len(intelligence.primary_services) > 0, 0.05),
            (len(intelligence.social_media_profiles) > 0, 0.05),
        ]
        
        for has_data, weight in scoring_factors:
            max_score += weight
            if has_data:
                score += weight
        
        return min(score / max_score if max_score > 0 else 0, 1.0)
    
    def _fallback_content(self, intelligence: PersonalizationIntelligence) -> PersonalizedContent:
        """
        Minimal fallback content if LLM fails.
        Still better than pure templates because it uses the data.
        """
        
        content = PersonalizedContent()
        
        # Use available data for basic personalization
        business_name = intelligence.business_name or "your business"
        
        content.subject_lines = [
            f"Quick question for {business_name}",
            f"Idea to help {business_name} grow",
        ]
        
        content.opening_lines = [
            f"I've been researching {business_name} and noticed some opportunities.",
        ]
        
        content.value_propositions = [
            "I can help modernize your digital presence and increase revenue.",
        ]
        
        content.pain_points_addressed = intelligence.pain_points_addressed[:3]
        content.personalization_score = 0.3
        content.confidence_level = "low"
        
        return content


# Convenience function for backward compatibility
async def generate_llm_personalized_content(
    intelligence: PersonalizationIntelligence,
    campaign_context: Optional[Dict] = None
) -> PersonalizedContent:
    """
    Generate personalized content using LLM with all available intelligence.
    
    This is the main entry point that should be used instead of templates.
    """
    
    engine = LLMPersonalizationEngine(campaign_context)
    return await engine.generate_personalized_content(intelligence)