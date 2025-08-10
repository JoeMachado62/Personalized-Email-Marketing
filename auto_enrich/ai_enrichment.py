"""
Enhanced AI enrichment module with advanced content generation capabilities.

This module provides backward compatibility with the original interface while
leveraging the new advanced content generation system. It now supports:
- Multiple LLM providers with fallback strategies
- Cost tracking and optimization
- Quality scoring for generated content
- Industry-specific prompts for car dealerships
- Caching for improved performance and cost efficiency

The module maintains the original API while adding enhanced features through
the new content generation system.
"""

from __future__ import annotations

import asyncio
import re
import sys
import os
from typing import Optional, Tuple

import httpx

from .config import LLM_API_KEY, LLM_MODEL_NAME, API_TIMEOUT

# Add the app directory to the Python path to import our enhanced services
current_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.join(os.path.dirname(current_dir), 'app')
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

try:
    from services.content_generator import content_generator, ContentRequest
    from prompts.templates import DealershipType, EmailTone
    ENHANCED_SYSTEM_AVAILABLE = True
except ImportError:
    ENHANCED_SYSTEM_AVAILABLE = False


async def _call_language_model(prompt: str) -> str:
    """Send a request to the OpenAI Chat Completion API.

    This function performs an asynchronous POST request to the
    OpenAI API. It expects a global API key defined in the
    environment. If the key is not set, it raises a RuntimeError.

    Args:
        prompt: The prompt string to send to the LLM.

    Returns:
        The model's generated text as a string.
    """
    if not LLM_API_KEY:
        raise RuntimeError(
            "LLM_API_KEY is not set. Please configure your API key in the .env file."
        )
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": LLM_MODEL_NAME,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that writes marketing copy."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 300,
        "temperature": 0.7,
    }
    async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()


def _derive_owner_name_from_email(email: str) -> Tuple[Optional[str], Optional[str]]:
    """Attempt to derive first and last names from an email address.

    The heuristic splits the email local part (before the @) by
    delimiters like dots, underscores or hyphens. It capitalises
    components to form a plausible first and last name. If the local
    part is a single token, it returns the token as the first name and
    leaves the last name as None.

    Args:
        email: An email address string.

    Returns:
        A tuple `(first_name, last_name)` where either part may be None.
    """
    local = email.split("@")[0]
    parts = re.split(r"[._-]", local)
    if not parts:
        return None, None
    if len(parts) == 1:
        return parts[0].capitalize(), None
    # Assume the first token is the first name and the last token is the last name
    first_name = parts[0].capitalize()
    last_name = parts[-1].capitalize()
    return first_name, last_name


async def generate_email_content(
    dealer_name: str,
    city: str,
    current_website: Optional[str],
    owner_email: Optional[str],
    extra_context: Optional[str] = None,
) -> Tuple[str, str, str]:
    """Generate personalized subject, icebreaker and hot button topic.

    Enhanced version that uses the advanced content generation system when available,
    with fallback to the original implementation for backward compatibility.

    Args:
        dealer_name: Official name of the dealership.
        city: City where the dealer is located.
        current_website: URL of the dealer's website, if known.
        owner_email: Owner or dealer email address.
        extra_context: Additional human-supplied context about the dealer.

    Returns:
        A tuple `(subject, icebreaker, hot_button_topic)`.
    """
    if ENHANCED_SYSTEM_AVAILABLE:
        try:
            # Use the enhanced content generation system
            request = ContentRequest(
                dealership_name=dealer_name,
                city=city,
                website=current_website,
                owner_email=owner_email,
                dealership_type=DealershipType.USED_CAR,  # Default assumption
                extra_context=extra_context,
                tones=[EmailTone.PROFESSIONAL],  # Use professional tone for backward compatibility
                max_cost_per_record=0.02
            )
            
            generated_content = await content_generator.generate_content(request)
            
            if generated_content.variations:
                # Use the first (and only) variation
                variation = generated_content.variations[0]
                return variation.subject, variation.icebreaker, variation.hot_button
        
        except Exception:
            # Fall back to original implementation if enhanced system fails
            pass
    
    # Original implementation as fallback
    owner_hint = ""
    if owner_email:
        first, last = _derive_owner_name_from_email(owner_email)
        if first:
            owner_hint = f"The owner's first name appears to be {first}."
        if last:
            owner_hint += f" The last name may be {last}."
    context = extra_context or ""
    
    # Enhanced prompt with better instructions for car dealerships
    prompt = (
        f"You are a professional marketing specialist creating personalized outreach for a car dealership owner.\n\n"
        f"DEALERSHIP DETAILS:\n"
        f"Name: {dealer_name}\n"
        f"Location: {city}\n"
        f"Website: {current_website or 'Not available'}\n"
        f"{owner_hint}\n"
        f"Additional Context: {context}\n\n"
        f"CREATE 3 COMPONENTS:\n"
        f"1. SUBJECT: Professional email subject line (6-8 words) with owner's name if known\n"
        f"2. ICEBREAKER: 2-3 sentences showing knowledge of their dealership and establishing credibility\n"
        f"3. HOT_BUTTON: One specific business challenge this type of dealer typically faces\n\n"
        f"REQUIREMENTS:\n"
        f"- Reference specific dealership details when possible\n"
        f"- Focus on automotive industry challenges\n"
        f"- Professional tone suitable for business owner\n"
        f"- Avoid generic marketing language\n\n"
        f"FORMAT YOUR RESPONSE AS:\n"
        f"SUBJECT: [your subject line]\n"
        f"ICEBREAKER: [your icebreaker text]\n"
        f"HOT_BUTTON: [specific business challenge]"
    )
    
    response = await _call_language_model(prompt)
    
    # Enhanced parsing with better error handling
    subject, icebreaker, hot_button = "", "", ""
    
    lines = response.split('\n')
    current_section = None
    content_buffer = []
    
    for line in lines:
        line = line.strip()
        if line.startswith("SUBJECT:"):
            if current_section and content_buffer:
                _assign_content(current_section, content_buffer, locals())
            current_section = "subject"
            content_buffer = [line[8:].strip()]  # Remove "SUBJECT:" prefix
        elif line.startswith("ICEBREAKER:"):
            if current_section and content_buffer:
                _assign_content(current_section, content_buffer, locals())
            current_section = "icebreaker"
            content_buffer = [line[11:].strip()]  # Remove "ICEBREAKER:" prefix
        elif line.startswith("HOT_BUTTON:"):
            if current_section and content_buffer:
                _assign_content(current_section, content_buffer, locals())
            current_section = "hot_button"
            content_buffer = [line[11:].strip()]  # Remove "HOT_BUTTON:" prefix
        elif line and current_section:
            content_buffer.append(line)
    
    # Handle the last section
    if current_section and content_buffer:
        _assign_content(current_section, content_buffer, locals())
    
    # Fallback parsing for simpler responses
    if not subject or not icebreaker or not hot_button:
        for line in response.splitlines():
            if line.startswith("SUBJECT:") and not subject:
                subject = line[len("SUBJECT:"):].strip()
            elif line.startswith("ICEBREAKER:") and not icebreaker:
                icebreaker = line[len("ICEBREAKER:"):].strip()
            elif line.startswith("HOT_BUTTON:") and not hot_button:
                hot_button = line[len("HOT_BUTTON:"):].strip()
    
    return subject, icebreaker, hot_button


def _assign_content(section: str, content_buffer: list, local_vars: dict):
    """Helper function to assign parsed content to appropriate variables."""
    content = ' '.join(content_buffer).strip()
    if section == "subject":
        local_vars["subject"] = content
    elif section == "icebreaker":
        local_vars["icebreaker"] = content
    elif section == "hot_button":
        local_vars["hot_button"] = content


async def generate_enhanced_email_content(
    dealer_name: str,
    city: str,
    current_website: Optional[str],
    owner_email: Optional[str],
    dealership_type: str = "used_car",
    extra_context: Optional[str] = None,
    tones: Optional[list] = None
) -> dict:
    """Generate enhanced email content with multiple tone variations.
    
    This function provides access to the advanced content generation system
    with multiple email tones, quality scoring, and detailed metrics.
    
    Args:
        dealer_name: Official name of the dealership.
        city: City where the dealer is located.
        current_website: URL of the dealer's website, if known.
        owner_email: Owner or dealer email address.
        dealership_type: Type of dealership (used_car, new_car, luxury, etc.).
        extra_context: Additional context about the dealer.
        tones: List of email tones to generate (professional, friendly, urgent).
    
    Returns:
        Dictionary with generated content variations, costs, and quality scores.
    """
    if not ENHANCED_SYSTEM_AVAILABLE:
        # Fall back to basic generation
        subject, icebreaker, hot_button = await generate_email_content(
            dealer_name, city, current_website, owner_email, extra_context
        )
        return {
            "variations": [{
                "tone": "professional",
                "subject": subject,
                "icebreaker": icebreaker,
                "hot_button": hot_button,
                "quality_scores": {"overall_score": 75.0},
                "cost": 0.01
            }],
            "total_cost": 0.01,
            "quality_summary": {"overall_quality": 75.0}
        }
    
    try:
        # Map string dealership type to enum
        dealership_type_map = {
            "used_car": DealershipType.USED_CAR,
            "new_car": DealershipType.NEW_CAR,
            "luxury": DealershipType.LUXURY,
            "commercial": DealershipType.COMMERCIAL,
            "motorcycle": DealershipType.MOTORCYCLE,
            "rv_boat": DealershipType.RV_BOAT,
        }
        
        dealership_enum = dealership_type_map.get(dealership_type, DealershipType.USED_CAR)
        
        # Map tone strings to enums
        tone_map = {
            "professional": EmailTone.PROFESSIONAL,
            "friendly": EmailTone.FRIENDLY,
            "urgent": EmailTone.URGENT
        }
        
        if tones:
            email_tones = [tone_map.get(tone, EmailTone.PROFESSIONAL) for tone in tones]
        else:
            email_tones = [EmailTone.PROFESSIONAL, EmailTone.FRIENDLY, EmailTone.URGENT]
        
        request = ContentRequest(
            dealership_name=dealer_name,
            city=city,
            website=current_website,
            owner_email=owner_email,
            dealership_type=dealership_enum,
            extra_context=extra_context,
            tones=email_tones,
            max_cost_per_record=0.02
        )
        
        generated_content = await content_generator.generate_content(request)
        quality_summary = content_generator.get_quality_summary(generated_content)
        
        # Convert to dictionary format
        variations_data = []
        for variation in generated_content.variations:
            variations_data.append({
                "tone": variation.tone.value,
                "subject": variation.subject,
                "icebreaker": variation.icebreaker,
                "hot_button": variation.hot_button,
                "quality_scores": variation.quality_scores,
                "tokens_used": variation.tokens_used,
                "cost": variation.cost,
                "generation_time": variation.generation_time,
                "cached": variation.cached
            })
        
        return {
            "dealership_name": generated_content.dealership_name,
            "city": generated_content.city,
            "owner_name": generated_content.owner_name,
            "variations": variations_data,
            "total_cost": generated_content.total_cost,
            "total_tokens": generated_content.total_tokens,
            "generation_time": generated_content.generation_time,
            "quality_summary": quality_summary
        }
        
    except Exception as e:
        # Fall back to basic generation
        subject, icebreaker, hot_button = await generate_email_content(
            dealer_name, city, current_website, owner_email, extra_context
        )
        return {
            "variations": [{
                "tone": "professional",
                "subject": subject,
                "icebreaker": icebreaker,
                "hot_button": hot_button,
                "quality_scores": {"overall_score": 75.0},
                "cost": 0.01,
                "error": str(e)
            }],
            "total_cost": 0.01,
            "quality_summary": {"overall_quality": 75.0, "recommendations": ["Fallback mode used"]}
        }
