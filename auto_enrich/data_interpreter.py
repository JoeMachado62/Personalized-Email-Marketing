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
    
    def _prepare_data_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare a concise summary of scraped data for AI processing"""
        summary = {
            'company': data.get('company_name'),
            'location': data.get('location'),
            'website': data.get('website_url')
        }
        
        # Add multi-source profile if available (NEW)
        if data.get('multi_source_profile'):
            profile = data['multi_source_profile']
            summary['multi_source_profile'] = {
                'sources_used': profile.get('sources_used', []),
                'owner_info': profile.get('owner_info', {}),
                'recent_activity': profile.get('recent_activity', [])[:3],
                'pain_points': list(set(profile.get('pain_points', [])))[:5],
                'achievements': profile.get('achievements', [])[:3],
                'social_presence': profile.get('social_presence', {}),
                'reputation': profile.get('reputation', {}),
                'personalization_hooks': profile.get('personalization_hooks', [])[:5]
            }
            
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
        
        # Prepare concise data summary
        data_summary = self._prepare_data_summary(scraped_data)
        
        # Single comprehensive prompt for all extractions
        batch_prompt = f"""
        Analyze the following scraped data and extract ALL requested information in a single response.
        
        DATA TO ANALYZE:
        {json.dumps(data_summary, indent=2)[:4000]}  # Increased limit for batch processing
        
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
                    {"role": "system", "content": "You are a data extraction specialist. Extract only factual information present in the provided data. Return valid JSON."},
                    {"role": "user", "content": batch_prompt}
                ],
                "max_tokens": 500,  # Increased for batch response
                "temperature": 0.3,  # Low temperature for factual extraction
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