"""
AI Data Interpreter - Uses LLM ONLY to interpret scraped data, not generate from scratch.
This significantly reduces costs by limiting AI usage to data interpretation.
"""

import json
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

import httpx

from .config import LLM_API_KEY, LLM_MODEL_NAME, API_TIMEOUT

logger = logging.getLogger(__name__)


class DataInterpreter:
    """
    Interprets scraped web data using AI to extract structured information.
    Uses AI minimally - only for interpretation, not generation.
    """
    
    def __init__(self, custom_prompts: Optional[Dict[str, str]] = None):
        """
        Initialize with optional custom prompts.
        
        Args:
            custom_prompts: Dictionary of custom prompts for different data types
        """
        self.custom_prompts = custom_prompts or {}
        self.default_prompts = self._get_default_prompts()
    
    def _get_default_prompts(self) -> Dict[str, str]:
        """Get default system prompts for data interpretation"""
        return {
            'extract_owner': """
                From the provided scraped data, extract the owner or key decision maker's information.
                Look for: CEO, President, Owner, Founder, General Manager.
                Return ONLY what you find in the data, do not generate or guess.
                Format: {"first_name": "", "last_name": "", "title": "", "confidence": 0-100}
            """,
            
            'extract_business_details': """
                From the scraped data, extract factual business details.
                Look for: specializations, years in business, unique selling points, inventory types.
                Return ONLY information found in the data, not assumptions.
                Format: {"specialization": "", "years_in_business": null, "unique_features": [], "inventory_focus": ""}
            """,
            
            'identify_pain_points': """
                Based on the scraped website and search data, identify potential business challenges.
                Look for: missing features on website, outdated design, limited online presence, no reviews.
                Base this ONLY on observed data, not general assumptions.
                Format: {"observed_issues": [], "missing_features": [], "opportunities": []}
            """,
            
            'create_email_subject': """
                Using the extracted company data, create a personalized subject line.
                Include specific details found in the data (location, specialization, owner name if known).
                Maximum 10 words. Use ONLY factual information from the data provided.
            """,
            
            'create_icebreaker': """
                Using the scraped data, create a personalized opening that shows you've researched them.
                Reference specific facts found: their location, specialization, years in business, recent updates.
                Maximum 2 sentences. Use ONLY factual information from the data provided.
            """,
            
            'identify_hot_button': """
                Based on the observed data and identified issues, suggest ONE specific business challenge.
                This must be based on actual observations from their website/presence, not generic assumptions.
                Examples: "No mobile-responsive website observed" or "No online inventory system found"
            """
        }
    
    async def interpret_data(self, scraped_data: Dict[str, Any], 
                            interpretation_goals: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Interpret scraped data using AI to extract structured information.
        
        Args:
            scraped_data: Raw data gathered from web scraping
            interpretation_goals: Optional custom goals for what to extract
            
        Returns:
            Structured interpretation of the data
        """
        interpreted = {
            'company_name': scraped_data.get('company_name'),
            'location': scraped_data.get('location'),
            'timestamp': datetime.utcnow().isoformat(),
            'source_data': {
                'website_found': bool(scraped_data.get('website_url')),
                'search_results_count': len(scraped_data.get('search_results', [])),
                'data_quality': self._assess_data_quality(scraped_data)
            },
            'extracted_info': {},
            'generated_content': {},
            'confidence_scores': {}
        }
        
        try:
            # Batch all extractions into a single API call to reduce costs
            if scraped_data.get('search_results') or scraped_data.get('website_data'):
                # We have data to interpret
                all_extracted = await self._batch_extract_with_ai(scraped_data)
                
                # Parse the batched response
                interpreted['extracted_info']['owner'] = all_extracted.get('owner', {})
                interpreted['extracted_info']['business_details'] = all_extracted.get('business_details', {})
                interpreted['extracted_info']['pain_points'] = all_extracted.get('pain_points', {})
                interpreted['generated_content'] = all_extracted.get('email_content', {})
            else:
                # No data to interpret
                logger.warning(f"No web data found for {scraped_data.get('company_name')}")
                interpreted['extracted_info'] = {
                    'owner': {},
                    'business_details': {},
                    'pain_points': {}
                }
                interpreted['generated_content'] = {}
            
            # Calculate confidence scores
            interpreted['confidence_scores'] = self._calculate_confidence(scraped_data, interpreted)
            
        except Exception as e:
            logger.error(f"Error interpreting data: {str(e)}")
            interpreted['error'] = str(e)
        
        return interpreted
    
    def _assess_data_quality(self, scraped_data: Dict[str, Any]) -> str:
        """Assess the quality of scraped data"""
        score = 0
        
        if scraped_data.get('website_url'):
            score += 30
        if scraped_data.get('website_data', {}).get('contact_info'):
            score += 20
        if scraped_data.get('business_info'):
            score += 20
        if len(scraped_data.get('search_results', [])) > 3:
            score += 15
        if scraped_data.get('website_data', {}).get('about_text'):
            score += 15
            
        if score >= 80:
            return 'high'
        elif score >= 50:
            return 'medium'
        else:
            return 'low'
    
    async def _extract_with_ai(self, data: Dict[str, Any], prompt: str, task_name: str) -> Dict[str, Any]:
        """
        Use AI to extract specific information from scraped data.
        """
        if not LLM_API_KEY:
            logger.error("No LLM API key configured")
            return {'error': 'No API key'}
        
        # Prepare concise data summary for AI
        data_summary = self._prepare_data_summary(data)
        
        full_prompt = f"""
        {prompt}
        
        DATA TO ANALYZE:
        {json.dumps(data_summary, indent=2)[:3000]}  # Limit to 3000 chars to save tokens
        
        IMPORTANT: Only extract information that is explicitly present in the data.
        Do not generate or assume information that is not there.
        """
        
        try:
            headers = {
                "Authorization": f"Bearer {LLM_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": LLM_MODEL_NAME,
                "messages": [
                    {"role": "system", "content": "You are a data extraction specialist. Extract only factual information present in the provided data."},
                    {"role": "user", "content": full_prompt}
                ],
                "max_tokens": 200,  # Keep tokens low for extraction tasks
                "temperature": 0.3,  # Low temperature for factual extraction
            }
            
            async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                result = data["choices"][0]["message"]["content"].strip()
                
                # Try to parse as JSON if expected
                try:
                    return json.loads(result)
                except:
                    return {'raw_response': result}
                    
        except Exception as e:
            logger.error(f"AI extraction error for {task_name}: {str(e)}")
            return {'error': str(e)}
    
    def _prepare_enhanced_data_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare an enhanced, well-structured summary of all collected data"""
        summary = {
            'company_name': data.get('company_name'),
            'location': data.get('location'),
            'website_url': data.get('website_url'),
        }
        
        # PRIORITIZED: Owner and personnel information
        personnel_info = {'owners': [], 'team_members': []}
        
        # Extract from multi-source profile
        if data.get('multi_source_profile'):
            profile = data['multi_source_profile']
            
            # Owner information with high priority
            if profile.get('owner_info'):
                owner = profile['owner_info']
                personnel_info['owners'].append({
                    'name': f"{owner.get('first_name', '')} {owner.get('last_name', '')}".strip() or owner.get('full_name'),
                    'title': owner.get('title'),
                    'source': owner.get('source', 'web')
                })
            
            # All personnel for context (from Sunbiz or website)
            if profile.get('all_personnel'):
                personnel_info['team_members'] = profile['all_personnel']
            
            # Business details from Maps and website
            summary['business_details'] = {
                'type': profile.get('business_details', {}).get('type'),
                'rating': profile.get('business_details', {}).get('rating'),
                'hours': profile.get('business_details', {}).get('hours'),
                'phone_numbers': profile.get('contact_info', {}).get('phones', []),
                'emails': profile.get('contact_info', {}).get('emails', []),
                'websites': profile.get('contact_info', {}).get('websites', [])
            }
            
            # Corporate information from Sunbiz
            if profile.get('registry_data'):
                registry = profile['registry_data']
                summary['corporate_info'] = {
                    'entity_type': registry.get('entity_type'),
                    'fein': registry.get('filing_info', {}).get('fein'),
                    'date_filed': registry.get('filing_info', {}).get('date_filed'),
                    'status': registry.get('filing_info', {}).get('status'),
                    'registered_agent': registry.get('registered_agent', {}).get('name')
                }
                
                # Add authorized persons
                for person in registry.get('authorized_persons', []):
                    personnel_info['owners'].append({
                        'name': person.get('full_name'),
                        'title': person.get('title'),
                        'source': 'sunbiz'
                    })
                
                # Add officers as team members
                for officer in registry.get('officers', []):
                    personnel_info['team_members'].append(
                        f"{officer.get('full_name')} ({officer.get('title')})"
                    )
            
            # Website content summary
            if profile.get('combined_content'):
                summary['website_content'] = {
                    'sample': profile['combined_content'][:3000],  # First 3000 chars
                    'total_chars': profile.get('total_content_chars', 0),
                    'pages_scraped': profile.get('urls_scraped', 0)
                }
                # Also add as rich_content for AI processing
                summary['rich_content'] = profile['combined_content'][:5000]
            
            # Include all the existing profile data
            summary['multi_source_profile'] = profile
        
        # Add the personnel info to summary
        summary['personnel'] = personnel_info
        
        # Add Maps data if available (hours, rating, etc.)
        if data.get('maps_data'):
            maps = data['maps_data']
            summary['google_maps_info'] = {
                'business_name': maps.get('title'),
                'address': maps.get('address'),
                'phone': maps.get('phone'),
                'website': maps.get('website'),
                'rating': maps.get('rating'),
                'rating_count': maps.get('rating_count'),
                'business_type': maps.get('type'),
                'hours': maps.get('hours')
            }
        
        # Keep existing data as well
        if data.get('website_data'):
            summary['website_data'] = data['website_data']
        
        if data.get('search_results'):
            summary['search_results'] = data['search_results'][:5]
        
        if data.get('campaign_context'):
            summary['campaign_context'] = data['campaign_context']
            
        return summary
    
    def _prepare_data_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare a concise summary of scraped data for AI processing"""
        summary = {
            'company': data.get('company_name'),
            'location': data.get('location'),
            'website': data.get('website_url')
        }
        
        # Add multi-source profile if available (ENHANCED)
        if data.get('multi_source_profile'):
            profile = data['multi_source_profile']
            summary['multi_source_profile'] = {
                'sources_used': profile.get('sources_used', []),
                'urls_scraped': profile.get('urls_scraped', 0),
                'total_content_chars': profile.get('total_content_chars', 0),
                'owner_info': profile.get('owner_info', {}),
                'business_details': profile.get('business_details', {}),
                'contact_info': profile.get('contact_info', {}),
                'social_media': profile.get('social_media', {}),
                'recent_activity': profile.get('recent_activity', [])[:5],
                'pain_points': list(set(profile.get('pain_points', [])))[:7],
                'achievements': profile.get('achievements', [])[:5],
                'reviews': profile.get('reviews', [])[:3],
                'registry_data': profile.get('registry_data', {})
            }
            
            # Add combined content for AI processing (truncated)
            if profile.get('combined_content'):
                summary['rich_content'] = profile['combined_content'][:5000]
            
            # If we have personalization hooks, add them prominently
            if profile.get('personalization_hooks'):
                summary['recommended_hooks'] = [
                    hook['hook'] for hook in profile['personalization_hooks'][:3]
                ]
        
        # Add key website data
        if data.get('website_data'):
            wd = data['website_data']
            summary['website_info'] = {
                'title': wd.get('title'),
                'description': wd.get('meta_description'),
                'contact': wd.get('contact_info'),
                'about': wd.get('about_text', [])[:500],  # First 500 chars
                'key_phrases': wd.get('key_phrases', [])[:5],
                'potential_owners': wd.get('potential_owners', [])
            }
        
        # Add search result snippets
        if data.get('search_results'):
            summary['search_snippets'] = [
                {
                    'title': r.get('title'),
                    'snippet': r.get('snippet', '')[:200]
                }
                for r in data['search_results'][:3]
            ]
        
        # Add business info
        if data.get('business_info'):
            summary['business_info'] = data['business_info']
        
        # Add campaign context if present
        if data.get('campaign_context'):
            summary['campaign_context'] = {
                'goal': data['campaign_context'].get('campaign_goal'),
                'focus': data['campaign_context'].get('personalization_focus'),
                'tone': data['campaign_context'].get('message_tone', 'professional')
            }
            
        return summary
    
    async def _batch_extract_with_ai(self, scraped_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Batch all extractions into a single API call to minimize costs.
        This reduces 6 API calls down to 1.
        """
        if not LLM_API_KEY:
            logger.error("No LLM API key configured")
            return {}
        
        # Prepare enhanced data summary with better structure
        data_summary = self._prepare_enhanced_data_summary(scraped_data)
        
        # Enhanced prompt for multi-source data
        batch_prompt = f"""
        BUSINESS DATA ANALYSIS:
        {json.dumps(data_summary, indent=2)[:10000]}  # Increased for richer context
        
        EXTRACT THE FOLLOWING (JSON format required):
        {{
            "owner": {{
                "first_name": "extracted first name or null",
                "last_name": "extracted last name or null",
                "title": "extracted title or null",
                "confidence": 0-100
            }},
            "business_details": {{
                "specialization": "what they specialize in",
                "years_in_business": null or number,
                "unique_features": [],
                "inventory_focus": "types of vehicles they focus on"
            }},
            "pain_points": {{
                "observed_issues": ["list of observed website/business issues"],
                "missing_features": ["features their website lacks"],
                "opportunities": ["potential improvements"]
            }},
            "email_content": {{
                "subject": {{
                    "raw_response": "10 word personalized subject using found details"
                }},
                "icebreaker": {{
                    "raw_response": "2 sentence personalized opening referencing specific found facts"
                }},
                "hot_button": {{
                    "raw_response": "ONE specific observed business challenge"
                }}
            }}
        }}
        
        IMPORTANT GUIDELINES:
        1. If "recommended_hooks" are provided, use them as inspiration for the icebreaker
        2. If "multi_source_profile" is available, prioritize that information
        3. Focus on recent_activity if available for timely personalization
        4. Use reputation/review data to identify real pain points
        5. Reference social media presence if found
        
        RULES:
        1. Only extract information explicitly present in the data
        2. Do not generate or assume information not there
        3. Use specific details from the scraped data
        4. Keep responses concise and factual
        """
        
        try:
            headers = {
                "Authorization": f"Bearer {LLM_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": LLM_MODEL_NAME,
                "messages": [
                    {"role": "system", "content": """You are a two-in-one expert:

First, act as a Data Analyst specializing in marketing personalization. Review the data dump which includes business information, corporate ownership details, and website content. Identify unique selling points, pain points, notable achievements, industry context, and anything that would allow for a highly personalized outreach message.

Second, switch roles to a Marketing Copywriter and transform these insights into engaging marketing material.

Your job is to produce:

Subject Line → A concise, high-impact subject line that feels personal, relevant, and likely to boost open rates.

Icebreaker Intro Paragraph → A warm, multi-line opening paragraph that references the specific business context and feels custom-written for this company. It should build rapport without being "salesy" and lead naturally into a segue line provided later in the campaign.

Guidelines:
- DO NOT repeat generic phrases like "I came across your website…" unless backed by specific context.
- Keep the subject line under 9 words.
- Make the icebreaker 3–4 short sentences max, each sentence naturally leading to the next.
- The tone should be friendly, credible, and human — avoid sounding like AI.
- Use details from the provided data wherever possible.
- If owner/manager names are provided, use them appropriately.
- Reference specific business details like years in business, location specifics, team members, or recent achievements.

Output Format:
SUBJECT_LINE: {short, punchy subject line here}
ICEBREAKER: {multi-line personalized intro paragraph here}

Return all requested data in valid JSON format."""},
                    {"role": "user", "content": batch_prompt}
                ],
                "max_tokens": 1000,  # Increased for richer content generation
                "temperature": 0.5,  # Balanced for creativity and accuracy
                "response_format": {"type": "json_object"}  # Ensure JSON response
            }
            
            async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                result = data["choices"][0]["message"]["content"].strip()
                
                # Parse JSON response
                try:
                    extracted = json.loads(result)
                    logger.info(f"Successfully batch extracted data for {scraped_data.get('company_name')}")
                    return extracted
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse batch extraction response: {e}")
                    return self._get_empty_extraction()
                    
        except Exception as e:
            logger.error(f"Batch AI extraction error: {str(e)}")
            return self._get_empty_extraction()
    
    def _get_empty_extraction(self) -> Dict[str, Any]:
        """Return empty extraction structure"""
        return {
            "owner": {},
            "business_details": {},
            "pain_points": {},
            "email_content": {
                "subject": {"raw_response": ""},
                "icebreaker": {"raw_response": ""},
                "hot_button": {"raw_response": ""}
            }
        }
    
    async def _generate_email_content(self, scraped_data: Dict[str, Any], 
                                     extracted_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        [DEPRECATED - Now handled in batch extraction]
        This method is kept for backwards compatibility but is no longer used.
        """
        return extracted_info.get('email_content', {}
        )
        
        return email_content
    
    def _calculate_confidence(self, scraped_data: Dict[str, Any], 
                            interpreted: Dict[str, Any]) -> Dict[str, float]:
        """Calculate confidence scores for extracted information"""
        scores = {}
        
        # Data quality score
        quality = scraped_data.get('source_data', {}).get('data_quality', 'low')
        quality_scores = {'high': 0.9, 'medium': 0.6, 'low': 0.3}
        base_score = quality_scores.get(quality, 0.3)
        
        # Owner confidence
        owner = interpreted.get('extracted_info', {}).get('owner', {})
        if owner.get('first_name') and owner.get('last_name'):
            scores['owner'] = min(base_score + 0.3, 1.0)
        elif owner.get('first_name') or owner.get('last_name'):
            scores['owner'] = base_score
        else:
            scores['owner'] = 0.2
        
        # Business details confidence
        if scraped_data.get('website_data'):
            scores['business_details'] = min(base_score + 0.2, 1.0)
        else:
            scores['business_details'] = base_score * 0.7
        
        # Email content confidence
        if interpreted.get('generated_content'):
            scores['email_content'] = base_score
        else:
            scores['email_content'] = 0.1
        
        scores['overall'] = sum(scores.values()) / len(scores) if scores else 0.0
        
        return scores


# Convenience function
async def interpret_scraped_data(scraped_data: Dict[str, Any],
                                custom_prompts: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Convenience function to interpret scraped data.
    
    Args:
        scraped_data: Data from web scraper
        custom_prompts: Optional custom interpretation prompts
        
    Returns:
        Interpreted and structured data
    """
    interpreter = DataInterpreter(custom_prompts)
    return await interpreter.interpret_data(scraped_data)