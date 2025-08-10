"""
Advanced content generation service with multi-tone support, quality scoring, and cost optimization.

This service orchestrates content generation using the LLM service and prompt templates
to create high-quality, personalized email content for automotive dealerships.
"""

import asyncio
import re
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from app.services.llm_service import llm_service, LLMResponse, ContentTone
from app.prompts.templates import (
    DealershipPrompts, 
    EmailTone, 
    DealershipType, 
    QualityScorer,
    QUICK_TEMPLATES
)


@dataclass
class EmailVariation:
    """Single email variation with content and metadata."""
    tone: EmailTone
    subject: str
    icebreaker: str
    hot_button: str
    quality_scores: Dict[str, float]
    tokens_used: int
    cost: float
    generation_time: float
    cached: bool = False


@dataclass
class GeneratedContent:
    """Complete generated content with all variations."""
    dealership_name: str
    city: str
    owner_name: Optional[str]
    variations: List[EmailVariation]
    total_cost: float
    total_tokens: int
    generation_time: float
    timestamp: datetime


@dataclass
class ContentRequest:
    """Request for content generation."""
    dealership_name: str
    city: str
    website: Optional[str] = None
    owner_email: Optional[str] = None
    owner_name: Optional[str] = None
    dealership_type: DealershipType = DealershipType.USED_CAR
    extra_context: Optional[str] = None
    tones: List[EmailTone] = None
    max_cost_per_record: float = 0.02
    quality_threshold: float = 70.0


class ContentGenerator:
    """Advanced content generation with multi-tone support and optimization."""
    
    def __init__(self):
        self.quality_scorer = QualityScorer()
        self._generation_cache = {}  # Simple cache for expensive operations
    
    def _derive_owner_name_from_email(self, email: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract owner name from email address."""
        if not email or '@' not in email:
            return None, None
        
        local = email.split("@")[0]
        parts = re.split(r"[._-]", local)
        
        if not parts:
            return None, None
        
        if len(parts) == 1:
            return parts[0].capitalize(), None
        
        # Take first and last parts
        first_name = parts[0].capitalize()
        last_name = parts[-1].capitalize()
        
        # Filter out common non-name patterns
        non_names = {'info', 'sales', 'admin', 'contact', 'support', 'manager', 'owner'}
        
        if first_name.lower() in non_names:
            first_name = None
        if last_name.lower() in non_names:
            last_name = None
        
        return first_name, last_name
    
    def _parse_multi_tone_response(self, response: str, tones: List[EmailTone]) -> Dict[EmailTone, Dict[str, str]]:
        """Parse multi-tone LLM response into structured data."""
        results = {}
        
        for tone in tones:
            tone_key = tone.value.upper()
            results[tone] = {'subject': '', 'icebreaker': '', 'hot_button': ''}
            
            # Extract subject
            subject_pattern = f"TONE_{tone_key}_SUBJECT:\\s*(.+?)(?=\\n|$)"
            subject_match = re.search(subject_pattern, response, re.IGNORECASE | re.MULTILINE)
            if subject_match:
                results[tone]['subject'] = subject_match.group(1).strip()
            
            # Extract icebreaker
            icebreaker_pattern = f"TONE_{tone_key}_ICEBREAKER:\\s*(.+?)(?=TONE_|HOT_BUTTON|$)"
            icebreaker_match = re.search(icebreaker_pattern, response, re.IGNORECASE | re.DOTALL)
            if icebreaker_match:
                results[tone]['icebreaker'] = icebreaker_match.group(1).strip()
            
            # Extract hot button
            hot_button_pattern = f"TONE_{tone_key}_HOT_BUTTON:\\s*(.+?)(?=TONE_|$)"
            hot_button_match = re.search(hot_button_pattern, response, re.IGNORECASE | re.DOTALL)
            if hot_button_match:
                results[tone]['hot_button'] = hot_button_match.group(1).strip()
        
        return results
    
    def _parse_single_tone_response(self, response: str) -> Dict[str, str]:
        """Parse single-tone LLM response into structured data."""
        result = {'subject': '', 'icebreaker': '', 'hot_button': ''}
        
        # Extract subject
        subject_match = re.search(r"SUBJECT:\s*(.+?)(?=\n|$)", response, re.IGNORECASE | re.MULTILINE)
        if subject_match:
            result['subject'] = subject_match.group(1).strip()
        
        # Extract icebreaker
        icebreaker_match = re.search(r"ICEBREAKER:\s*(.+?)(?=HOT_BUTTON|$)", response, re.IGNORECASE | re.DOTALL)
        if icebreaker_match:
            result['icebreaker'] = icebreaker_match.group(1).strip()
        
        # Extract hot button
        hot_button_match = re.search(r"HOT_BUTTON:\s*(.+?)$", response, re.IGNORECASE | re.DOTALL)
        if hot_button_match:
            result['hot_button'] = hot_button_match.group(1).strip()
        
        return result
    
    async def _generate_single_variation(
        self,
        request: ContentRequest,
        tone: EmailTone,
        owner_name: Optional[str] = None
    ) -> EmailVariation:
        """Generate single email variation with specified tone."""
        start_time = time.time()
        
        # Build optimized prompt
        prompt = DealershipPrompts.build_single_tone_prompt(
            dealership_name=request.dealership_name,
            city=request.city,
            tone=tone,
            website=request.website,
            owner_name=owner_name,
            dealership_type=request.dealership_type,
            extra_context=request.extra_context
        )
        
        # Generate content
        try:
            llm_response = await llm_service.generate(
                prompt=prompt,
                temperature=0.7,
                max_tokens=400
            )
            
            # Parse response
            parsed_content = self._parse_single_tone_response(llm_response.content)
            
            # Calculate quality scores
            quality_scores = self.quality_scorer.score_complete_email(
                subject=parsed_content['subject'],
                icebreaker=parsed_content['icebreaker'],
                hot_button=parsed_content['hot_button'],
                dealership_name=request.dealership_name,
                city=request.city,
                owner_name=owner_name
            )
            
            generation_time = time.time() - start_time
            
            return EmailVariation(
                tone=tone,
                subject=parsed_content['subject'],
                icebreaker=parsed_content['icebreaker'],
                hot_button=parsed_content['hot_button'],
                quality_scores=quality_scores,
                tokens_used=llm_response.tokens_used,
                cost=llm_response.cost,
                generation_time=generation_time,
                cached=llm_response.cached
            )
            
        except Exception as e:
            # Return template-based fallback
            template = QUICK_TEMPLATES.get(tone, QUICK_TEMPLATES[EmailTone.PROFESSIONAL])
            
            fallback_subject = template.subject_template.format(
                owner_name=owner_name or "Owner",
                dealership_name=request.dealership_name
            )
            
            fallback_icebreaker = template.icebreaker_template.format(
                owner_name=owner_name or "Owner",
                dealership_name=request.dealership_name,
                city=request.city,
                dealership_type=request.dealership_type.value.replace("_", " "),
                unique_aspect="market presence"
            )
            
            fallback_hot_button = template.hot_button_template.format(
                dealership_type=request.dealership_type.value.replace("_", " "),
                improvement_area="customer acquisition",
                common_challenge="lead generation",
                urgent_challenge="digital marketing optimization",
                metric_area="qualified leads"
            )
            
            quality_scores = self.quality_scorer.score_complete_email(
                subject=fallback_subject,
                icebreaker=fallback_icebreaker,
                hot_button=fallback_hot_button,
                dealership_name=request.dealership_name,
                city=request.city,
                owner_name=owner_name
            )
            
            return EmailVariation(
                tone=tone,
                subject=fallback_subject,
                icebreaker=fallback_icebreaker,
                hot_button=fallback_hot_button,
                quality_scores=quality_scores,
                tokens_used=0,
                cost=0.0,
                generation_time=time.time() - start_time,
                cached=False
            )
    
    async def _generate_multi_tone_batch(
        self,
        request: ContentRequest,
        tones: List[EmailTone],
        owner_name: Optional[str] = None
    ) -> List[EmailVariation]:
        """Generate multiple email variations in a single API call."""
        start_time = time.time()
        
        # Build optimized multi-tone prompt
        prompt = DealershipPrompts.build_optimized_prompt(
            dealership_name=request.dealership_name,
            city=request.city,
            website=request.website,
            owner_name=owner_name,
            dealership_type=request.dealership_type,
            extra_context=request.extra_context,
            tones=tones
        )
        
        try:
            llm_response = await llm_service.generate(
                prompt=prompt,
                temperature=0.7,
                max_tokens=800  # More tokens for multiple variations
            )
            
            # Parse multi-tone response
            parsed_content = self._parse_multi_tone_response(llm_response.content, tones)
            
            variations = []
            
            for tone in tones:
                if tone in parsed_content:
                    content = parsed_content[tone]
                    
                    # Calculate quality scores
                    quality_scores = self.quality_scorer.score_complete_email(
                        subject=content['subject'],
                        icebreaker=content['icebreaker'],
                        hot_button=content['hot_button'],
                        dealership_name=request.dealership_name,
                        city=request.city,
                        owner_name=owner_name
                    )
                    
                    variation = EmailVariation(
                        tone=tone,
                        subject=content['subject'],
                        icebreaker=content['icebreaker'],
                        hot_button=content['hot_button'],
                        quality_scores=quality_scores,
                        tokens_used=llm_response.tokens_used // len(tones),  # Approximate
                        cost=llm_response.cost / len(tones),  # Distribute cost
                        generation_time=(time.time() - start_time) / len(tones),
                        cached=llm_response.cached
                    )
                    
                    variations.append(variation)
            
            return variations
            
        except Exception as e:
            # Fall back to individual generation
            variations = []
            for tone in tones:
                try:
                    variation = await self._generate_single_variation(request, tone, owner_name)
                    variations.append(variation)
                except Exception:
                    continue
            
            return variations
    
    async def generate_content(self, request: ContentRequest) -> GeneratedContent:
        """Generate complete email content with all requested variations."""
        start_time = time.time()
        
        # Derive owner name if not provided
        owner_name = request.owner_name
        if not owner_name and request.owner_email:
            first_name, last_name = self._derive_owner_name_from_email(request.owner_email)
            if first_name:
                owner_name = first_name
                if last_name:
                    owner_name = f"{first_name} {last_name}"
        
        # Default tones if not specified
        tones = request.tones or [EmailTone.PROFESSIONAL, EmailTone.FRIENDLY, EmailTone.URGENT]
        
        # Check cost estimate before generation
        estimated_cost = await self._estimate_generation_cost(request, tones)
        if estimated_cost > request.max_cost_per_record:
            # Use single API call for cost efficiency
            variations = await self._generate_multi_tone_batch(request, tones, owner_name)
        else:
            # Try batch generation first, fall back to individual if needed
            try:
                variations = await self._generate_multi_tone_batch(request, tones, owner_name)
                
                # If batch generation failed or quality is too low, try individual
                avg_quality = sum(v.quality_scores.get('overall_score', 0) for v in variations) / len(variations) if variations else 0
                
                if not variations or avg_quality < request.quality_threshold:
                    # Generate individual variations for better quality
                    individual_variations = []
                    for tone in tones[:2]:  # Limit to 2 to control costs
                        try:
                            variation = await self._generate_single_variation(request, tone, owner_name)
                            individual_variations.append(variation)
                        except Exception:
                            continue
                    
                    if individual_variations:
                        variations = individual_variations
                        
            except Exception:
                # Final fallback to template-based generation
                variations = []
                for tone in tones:
                    template = QUICK_TEMPLATES.get(tone, QUICK_TEMPLATES[EmailTone.PROFESSIONAL])
                    
                    subject = template.subject_template.format(
                        owner_name=owner_name or "Owner",
                        dealership_name=request.dealership_name
                    )
                    
                    icebreaker = template.icebreaker_template.format(
                        owner_name=owner_name or "Owner",
                        dealership_name=request.dealership_name,
                        city=request.city,
                        dealership_type=request.dealership_type.value.replace("_", " "),
                        unique_aspect="local market presence"
                    )
                    
                    hot_button = template.hot_button_template.format(
                        dealership_type=request.dealership_type.value.replace("_", " "),
                        improvement_area="customer acquisition"
                    )
                    
                    quality_scores = self.quality_scorer.score_complete_email(
                        subject, icebreaker, hot_button,
                        request.dealership_name, request.city, owner_name
                    )
                    
                    variation = EmailVariation(
                        tone=tone,
                        subject=subject,
                        icebreaker=icebreaker,
                        hot_button=hot_button,
                        quality_scores=quality_scores,
                        tokens_used=0,
                        cost=0.0,
                        generation_time=0.0,
                        cached=False
                    )
                    
                    variations.append(variation)
        
        # Calculate totals
        total_cost = sum(v.cost for v in variations)
        total_tokens = sum(v.tokens_used for v in variations)
        generation_time = time.time() - start_time
        
        return GeneratedContent(
            dealership_name=request.dealership_name,
            city=request.city,
            owner_name=owner_name,
            variations=variations,
            total_cost=total_cost,
            total_tokens=total_tokens,
            generation_time=generation_time,
            timestamp=datetime.now()
        )
    
    async def _estimate_generation_cost(
        self,
        request: ContentRequest,
        tones: List[EmailTone]
    ) -> float:
        """Estimate cost for generating content."""
        # Build sample prompt to estimate tokens
        sample_prompt = DealershipPrompts.build_optimized_prompt(
            dealership_name=request.dealership_name,
            city=request.city,
            website=request.website,
            owner_name=request.owner_name,
            dealership_type=request.dealership_type,
            extra_context=request.extra_context,
            tones=tones
        )
        
        return llm_service.estimate_cost(sample_prompt)
    
    async def generate_batch(
        self,
        requests: List[ContentRequest],
        max_concurrent: int = 3
    ) -> List[GeneratedContent]:
        """Generate content for multiple requests concurrently."""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def generate_with_limit(request):
            async with semaphore:
                return await self.generate_content(request)
        
        tasks = [generate_with_limit(request) for request in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and return successful results
        return [result for result in results if not isinstance(result, Exception)]
    
    def get_quality_summary(self, content: GeneratedContent) -> Dict[str, Any]:
        """Get quality summary for generated content."""
        if not content.variations:
            return {'overall_quality': 0, 'recommendations': ['No content generated']}
        
        # Calculate overall quality metrics
        quality_scores = []
        for variation in content.variations:
            quality_scores.append(variation.quality_scores.get('overall_score', 0))
        
        avg_quality = sum(quality_scores) / len(quality_scores)
        best_variation = max(content.variations, key=lambda v: v.quality_scores.get('overall_score', 0))
        
        # Generate recommendations
        recommendations = []
        
        if avg_quality < 70:
            recommendations.append("Consider providing more specific context about the dealership")
        
        if content.total_cost > 0.015:  # 75% of budget
            recommendations.append("High cost - consider using batch generation or caching")
        
        if best_variation.quality_scores.get('subject_score', 0) < 70:
            recommendations.append("Subject lines need improvement - consider more personalization")
        
        if best_variation.quality_scores.get('icebreaker_score', 0) < 70:
            recommendations.append("Icebreakers need more specific dealership details")
        
        return {
            'overall_quality': avg_quality,
            'best_variation_tone': best_variation.tone.value,
            'cost_efficiency': content.total_cost / max(avg_quality/100, 0.1),  # Cost per quality point
            'recommendations': recommendations or ['Content quality is good']
        }


# Global content generator instance
content_generator = ContentGenerator()