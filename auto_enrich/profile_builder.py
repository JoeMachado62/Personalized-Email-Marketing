"""
Profile Builder - Intelligent Multi-Source Data Collection
Prioritizes sources that provide valuable personalization opportunities
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlparse
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)


class ProfileBuilder:
    """
    Builds comprehensive business profiles by intelligently selecting
    and scraping multiple high-value sources.
    """
    
    # Source priority weights for personalization value
    SOURCE_PRIORITIES = {
        'linkedin': 10,      # Owner profiles, company updates, employee info
        'facebook': 9,       # Recent posts, events, community engagement
        'instagram': 8,      # Visual content, culture, recent activity
        'twitter': 8,        # Real-time updates, opinions, engagement
        'youtube': 7,        # Company videos, testimonials, culture
        'yelp': 9,          # Reviews reveal pain points and strengths
        'google': 9,        # Google reviews and My Business info
        'bbb': 7,           # Better Business Bureau - complaints/accreditation
        'news': 8,          # Recent news, announcements, changes
        'indeed': 6,        # Job postings reveal growth/challenges
        'glassdoor': 6,     # Employee reviews reveal culture
        'official': 10,     # Company's own website
        'directory': 4,     # Basic info, usually redundant
        'aggregator': 3,    # Often outdated or duplicate info
    }
    
    # Keywords that indicate high-value personalization content
    PERSONALIZATION_SIGNALS = {
        'recent_activity': ['announce', 'launch', 'new', 'expand', 'open', 'celebrate', 'award', 'promote'],
        'pain_points': ['complaint', 'issue', 'problem', 'challenge', 'difficult', 'frustrat', 'disappoint'],
        'achievements': ['award', 'recogni', 'certif', 'accredit', 'best', 'top', 'leader', 'excel'],
        'growth': ['hiring', 'expand', 'growth', 'new location', 'acquisition', 'partner'],
        'leadership': ['owner', 'ceo', 'president', 'founder', 'manager', 'director'],
        'culture': ['team', 'culture', 'values', 'mission', 'community', 'volunteer', 'sponsor']
    }
    
    def __init__(self, campaign_context: Optional[Dict[str, Any]] = None):
        """
        Initialize with campaign context to guide source selection.
        
        Args:
            campaign_context: Campaign goals and targeting information
        """
        self.campaign_context = campaign_context or {}
        self.personalization_focus = campaign_context.get('personalization_focus', 'recent_activity')
        self.target_information = campaign_context.get('target_information', [])
    
    def prioritize_search_results(self, search_results: List[Dict[str, Any]], 
                                 company_name: str) -> List[Dict[str, Any]]:
        """
        Prioritize search results based on their value for profile building.
        
        Args:
            search_results: List of search result dictionaries
            company_name: Company name for relevance scoring
            
        Returns:
            Prioritized list of search results
        """
        scored_results = []
        
        for result in search_results:
            url = result.get('url', '')
            title = result.get('title', '')
            snippet = result.get('snippet', '')
            
            # Calculate priority score
            score = self._calculate_source_score(url, title, snippet, company_name)
            
            # Add score to result
            result['priority_score'] = score
            result['source_type'] = self._identify_source_type(url)
            result['personalization_potential'] = self._assess_personalization_potential(
                title, snippet, url
            )
            
            scored_results.append(result)
        
        # Sort by priority score (highest first)
        scored_results.sort(key=lambda x: x['priority_score'], reverse=True)
        
        # Log the prioritization
        logger.info(f"Prioritized {len(scored_results)} search results")
        for i, result in enumerate(scored_results[:5]):
            logger.debug(f"  {i+1}. Score {result['priority_score']}: {result['source_type']} - {result.get('title', '')[:50]}")
        
        return scored_results
    
    def _calculate_source_score(self, url: str, title: str, snippet: str, 
                                company_name: str) -> float:
        """Calculate priority score for a search result."""
        score = 0.0
        
        # Base score from source type
        source_type = self._identify_source_type(url)
        score += self.SOURCE_PRIORITIES.get(source_type, 2)
        
        # Boost for exact company name match
        company_words = company_name.lower().split()
        if all(word in title.lower() or word in snippet.lower() 
               for word in company_words if len(word) > 3):
            score += 3
        
        # Boost for personalization signals in snippet
        all_text = (title + ' ' + snippet).lower()
        for signal_type, keywords in self.PERSONALIZATION_SIGNALS.items():
            if any(keyword in all_text for keyword in keywords):
                score += 2
                if signal_type == self.personalization_focus:
                    score += 3  # Extra boost if matches campaign focus
        
        # Boost for recency indicators
        current_year = datetime.now().year
        if str(current_year) in all_text or str(current_year - 1) in all_text:
            score += 2
        
        # Penalty for aggregators and directories
        if any(agg in url.lower() for agg in ['yellowpages', 'whitepages', 'manta', 'buzzfile']):
            score -= 3
        
        return score
    
    def _identify_source_type(self, url: str) -> str:
        """Identify the type of source from URL."""
        url_lower = url.lower()
        domain = urlparse(url).netloc.lower()
        
        # Social media platforms
        if 'linkedin.com' in domain:
            return 'linkedin'
        elif 'facebook.com' in domain or 'fb.com' in domain:
            return 'facebook'
        elif 'instagram.com' in domain:
            return 'instagram'
        elif 'twitter.com' in domain or 'x.com' in domain:
            return 'twitter'
        elif 'youtube.com' in domain:
            return 'youtube'
        
        # Review platforms
        elif 'yelp.com' in domain:
            return 'yelp'
        elif 'google.com' in domain and ('/maps/' in url_lower or '/search?' in url_lower):
            return 'google'
        elif 'bbb.org' in domain:
            return 'bbb'
        
        # Job/culture platforms
        elif 'indeed.com' in domain:
            return 'indeed'
        elif 'glassdoor.com' in domain:
            return 'glassdoor'
        
        # News
        elif any(news in domain for news in ['news', 'times', 'post', 'journal', 'herald', 'gazette']):
            return 'news'
        
        # Directories and aggregators
        elif any(dir in domain for dir in ['yellowpages', 'whitepages', 'manta', 'buzzfile', 'mapquest']):
            return 'directory'
        
        # Likely official website
        else:
            return 'official'
    
    def _assess_personalization_potential(self, title: str, snippet: str, url: str) -> Dict[str, Any]:
        """Assess the personalization potential of a search result."""
        potential = {
            'has_owner_info': False,
            'has_recent_activity': False,
            'has_pain_points': False,
            'has_achievements': False,
            'has_contact_info': False,
            'signals_found': []
        }
        
        all_text = (title + ' ' + snippet).lower()
        
        # Check for owner/leadership info
        if any(term in all_text for term in ['owner', 'ceo', 'president', 'founder']):
            potential['has_owner_info'] = True
            potential['signals_found'].append('leadership')
        
        # Check for recent activity
        current_year = datetime.now().year
        if str(current_year) in all_text or any(term in all_text for term in ['new', 'recent', 'announce']):
            potential['has_recent_activity'] = True
            potential['signals_found'].append('recent_activity')
        
        # Check for pain points (from reviews)
        if any(term in all_text for term in ['review', 'rating', 'complaint', 'issue']):
            potential['has_pain_points'] = True
            potential['signals_found'].append('reviews')
        
        # Check for achievements
        if any(term in all_text for term in ['award', 'best', 'top', 'certified']):
            potential['has_achievements'] = True
            potential['signals_found'].append('achievements')
        
        # Check for contact info
        if re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', all_text) or '@' in all_text:
            potential['has_contact_info'] = True
            potential['signals_found'].append('contact')
        
        return potential
    
    def select_sources_to_scrape(self, prioritized_results: List[Dict[str, Any]], 
                                 max_sources: int = 5) -> List[Dict[str, Any]]:
        """
        Select the best sources to scrape based on diversity and value.
        
        Args:
            prioritized_results: Pre-prioritized search results
            max_sources: Maximum number of sources to scrape
            
        Returns:
            Selected sources for scraping
        """
        selected = []
        source_types_included = set()
        
        # Always include the top result if it's the official website
        if prioritized_results and prioritized_results[0]['source_type'] == 'official':
            selected.append(prioritized_results[0])
            source_types_included.add('official')
        
        # Priority categories for diverse data collection
        priority_categories = [
            ['linkedin', 'facebook'],  # Social profiles
            ['yelp', 'google'],        # Reviews
            ['news'],                   # Recent updates
            ['official'],               # Company website
            ['instagram', 'twitter', 'youtube']  # Additional social
        ]
        
        # Select diverse high-value sources
        for category in priority_categories:
            for result in prioritized_results:
                if len(selected) >= max_sources:
                    break
                    
                source_type = result['source_type']
                if source_type in category and source_type not in source_types_included:
                    if result not in selected:
                        selected.append(result)
                        source_types_included.add(source_type)
                        break
        
        # Fill remaining slots with highest scored results
        for result in prioritized_results:
            if len(selected) >= max_sources:
                break
            if result not in selected:
                selected.append(result)
        
        logger.info(f"Selected {len(selected)} sources to scrape:")
        for i, source in enumerate(selected):
            logger.info(f"  {i+1}. {source['source_type']}: {source.get('title', '')[:50]}")
        
        return selected
    
    async def extract_profile_data(self, source: Dict[str, Any], 
                                   scraper_context) -> Dict[str, Any]:
        """
        Extract profile-relevant data from a source.
        
        Args:
            source: Source dictionary with URL and metadata
            scraper_context: Web scraper context for page access
            
        Returns:
            Extracted profile data
        """
        source_type = source.get('source_type', 'unknown')
        url = source.get('url', '')
        
        logger.info(f"Extracting profile data from {source_type}: {url[:50]}...")
        
        extracted_data = {
            'source_type': source_type,
            'url': url,
            'extraction_timestamp': datetime.now().isoformat(),
            'data': {}
        }
        
        try:
            # Source-specific extraction strategies
            if source_type == 'linkedin':
                extracted_data['data'] = await self._extract_linkedin_data(url, scraper_context)
            elif source_type == 'facebook':
                extracted_data['data'] = await self._extract_facebook_data(url, scraper_context)
            elif source_type in ['yelp', 'google']:
                extracted_data['data'] = await self._extract_review_data(url, scraper_context)
            elif source_type == 'news':
                extracted_data['data'] = await self._extract_news_data(url, scraper_context)
            else:
                # Generic extraction for other sources
                extracted_data['data'] = await self._extract_generic_data(url, scraper_context)
            
            extracted_data['success'] = True
            
        except Exception as e:
            logger.error(f"Failed to extract from {source_type}: {e}")
            extracted_data['success'] = False
            extracted_data['error'] = str(e)
        
        return extracted_data
    
    async def _extract_linkedin_data(self, url: str, context) -> Dict[str, Any]:
        """Extract LinkedIn profile or company data."""
        page = await context.new_page()
        data = {
            'profile_type': 'company' if '/company/' in url else 'person',
            'connections': [],
            'recent_posts': [],
            'about': ''
        }
        
        try:
            await page.goto(url, wait_until='networkidle', timeout=15000)
            
            # Extract based on profile type
            if data['profile_type'] == 'person':
                # Person profile extraction
                name_elem = await page.query_selector('h1')
                if name_elem:
                    data['name'] = await name_elem.inner_text()
                
                title_elem = await page.query_selector('.text-body-medium')
                if title_elem:
                    data['title'] = await title_elem.inner_text()
                    
            else:
                # Company profile extraction
                name_elem = await page.query_selector('h1')
                if name_elem:
                    data['company_name'] = await name_elem.inner_text()
                
                about_elem = await page.query_selector('.org-top-card-summary__tagline')
                if about_elem:
                    data['tagline'] = await about_elem.inner_text()
            
            # Look for contact info in about section
            about_section = await page.query_selector('[class*="about"]')
            if about_section:
                data['about'] = await about_section.inner_text()
                
        finally:
            await page.close()
        
        return data
    
    async def _extract_facebook_data(self, url: str, context) -> Dict[str, Any]:
        """Extract Facebook page data."""
        page = await context.new_page()
        data = {
            'recent_posts': [],
            'events': [],
            'reviews': [],
            'about': {}
        }
        
        try:
            await page.goto(url, wait_until='networkidle', timeout=15000)
            
            # Extract page name
            name_elem = await page.query_selector('h1')
            if name_elem:
                data['page_name'] = await name_elem.inner_text()
            
            # Look for recent posts (simplified extraction)
            posts = await page.query_selector_all('[role="article"]')
            for post in posts[:3]:  # Get top 3 recent posts
                post_text = await post.inner_text()
                if post_text:
                    data['recent_posts'].append({
                        'text': post_text[:200],
                        'has_engagement': 'Like' in post_text or 'Comment' in post_text
                    })
            
            # Look for contact/about info
            about_section = await page.query_selector('[aria-label*="About"]')
            if about_section:
                about_text = await about_section.inner_text()
                
                # Extract phone if present
                phone_match = re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', about_text)
                if phone_match:
                    data['about']['phone'] = phone_match.group()
                
                # Extract address if present
                if 'Get Directions' in about_text:
                    data['about']['has_address'] = True
                    
        finally:
            await page.close()
        
        return data
    
    async def _extract_review_data(self, url: str, context) -> Dict[str, Any]:
        """Extract review data from Yelp or Google."""
        page = await context.new_page()
        data = {
            'rating': None,
            'review_count': 0,
            'recent_reviews': [],
            'common_themes': {
                'positive': [],
                'negative': []
            }
        }
        
        try:
            await page.goto(url, wait_until='networkidle', timeout=15000)
            
            # Extract rating
            rating_elem = await page.query_selector('[aria-label*="rating"], [class*="rating"]')
            if rating_elem:
                rating_text = await rating_elem.inner_text()
                rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                if rating_match:
                    data['rating'] = float(rating_match.group(1))
            
            # Extract review snippets
            review_elements = await page.query_selector_all('[class*="review-content"], [class*="review-text"]')
            for review_elem in review_elements[:5]:  # Get top 5 reviews
                review_text = await review_elem.inner_text()
                if review_text:
                    data['recent_reviews'].append(review_text[:200])
                    
                    # Analyze sentiment themes
                    lower_text = review_text.lower()
                    if any(word in lower_text for word in ['great', 'excellent', 'amazing', 'love', 'best']):
                        data['common_themes']['positive'].append('satisfaction')
                    if any(word in lower_text for word in ['poor', 'bad', 'terrible', 'worst', 'disappoint']):
                        data['common_themes']['negative'].append('dissatisfaction')
                        
        finally:
            await page.close()
        
        return data
    
    async def _extract_news_data(self, url: str, context) -> Dict[str, Any]:
        """Extract news article data."""
        page = await context.new_page()
        data = {
            'headline': '',
            'date': '',
            'content_preview': '',
            'key_points': []
        }
        
        try:
            await page.goto(url, wait_until='networkidle', timeout=15000)
            
            # Extract headline
            headline_elem = await page.query_selector('h1')
            if headline_elem:
                data['headline'] = await headline_elem.inner_text()
            
            # Extract date
            date_elem = await page.query_selector('time, [class*="date"], [class*="publish"]')
            if date_elem:
                data['date'] = await date_elem.inner_text()
            
            # Extract article preview
            article_elem = await page.query_selector('article, [class*="article-body"], main')
            if article_elem:
                content = await article_elem.inner_text()
                data['content_preview'] = content[:500]
                
                # Extract key points from content
                for signal_type, keywords in self.PERSONALIZATION_SIGNALS.items():
                    if any(keyword in content.lower() for keyword in keywords):
                        data['key_points'].append(signal_type)
                        
        finally:
            await page.close()
        
        return data
    
    async def _extract_generic_data(self, url: str, context) -> Dict[str, Any]:
        """Generic extraction for any website."""
        from auto_enrich.web_scraper import WebDataGatherer
        
        # Use existing scraper logic for generic extraction
        gatherer = WebDataGatherer()
        gatherer.context = context
        return await gatherer._scrape_website(url)
    
    def synthesize_profile(self, multi_source_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Synthesize data from multiple sources into a comprehensive profile.
        
        Args:
            multi_source_data: List of extracted data from different sources
            
        Returns:
            Synthesized profile data
        """
        profile = {
            'sources_used': [],
            'confidence_scores': {},
            'owner_info': {},
            'company_info': {},
            'recent_activity': [],
            'pain_points': [],
            'achievements': [],
            'social_presence': {},
            'reputation': {},
            'personalization_hooks': []
        }
        
        for source_data in multi_source_data:
            if not source_data.get('success', False):
                continue
                
            source_type = source_data['source_type']
            data = source_data.get('data', {})
            profile['sources_used'].append(source_type)
            
            # Aggregate owner information
            if source_type == 'linkedin' and data.get('profile_type') == 'person':
                if data.get('name'):
                    profile['owner_info']['name'] = data['name']
                    profile['owner_info']['title'] = data.get('title', '')
                    profile['confidence_scores']['owner'] = 0.9
            
            # Aggregate recent activity
            if source_type in ['facebook', 'news']:
                if data.get('recent_posts'):
                    profile['recent_activity'].extend(data['recent_posts'])
                if data.get('headline'):
                    profile['recent_activity'].append({
                        'type': 'news',
                        'headline': data['headline'],
                        'date': data.get('date', '')
                    })
            
            # Aggregate pain points from reviews
            if source_type in ['yelp', 'google']:
                if data.get('common_themes', {}).get('negative'):
                    profile['pain_points'].extend(data['common_themes']['negative'])
                if data.get('rating'):
                    profile['reputation']['rating'] = data['rating']
                    profile['reputation']['review_count'] = data.get('review_count', 0)
            
            # Build social presence map
            if source_type in ['facebook', 'linkedin', 'instagram', 'twitter']:
                profile['social_presence'][source_type] = source_data['url']
        
        # Generate personalization hooks based on collected data
        profile['personalization_hooks'] = self._generate_personalization_hooks(profile)
        
        return profile
    
    def _generate_personalization_hooks(self, profile: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate specific personalization hooks from profile data."""
        hooks = []
        
        # Recent activity hooks
        if profile['recent_activity']:
            for activity in profile['recent_activity'][:2]:
                if isinstance(activity, dict) and activity.get('headline'):
                    hooks.append({
                        'type': 'recent_news',
                        'hook': f"Congratulations on {activity['headline']}",
                        'confidence': 'high'
                    })
        
        # Pain point hooks
        if profile['pain_points']:
            unique_pains = list(set(profile['pain_points']))
            for pain in unique_pains[:2]:
                hooks.append({
                    'type': 'pain_point',
                    'hook': f"I help businesses overcome {pain} challenges",
                    'confidence': 'medium'
                })
        
        # Social proof hooks
        if profile.get('reputation', {}).get('rating'):
            rating = profile['reputation']['rating']
            if rating >= 4.5:
                hooks.append({
                    'type': 'achievement',
                    'hook': f"Your {rating}-star rating shows exceptional customer service",
                    'confidence': 'high'
                })
        
        # Owner-specific hooks
        if profile.get('owner_info', {}).get('name'):
            owner_name = profile['owner_info']['name'].split()[0]  # First name
            hooks.append({
                'type': 'personal',
                'hook': f"Hi {owner_name}, I noticed your business",
                'confidence': 'high'
            })
        
        return hooks


# Integration function for existing pipeline
async def build_enriched_profile(search_results: List[Dict[str, Any]], 
                                 company_name: str,
                                 campaign_context: Dict[str, Any],
                                 web_context) -> Dict[str, Any]:
    """
    Main integration point for multi-source profile building.
    
    Args:
        search_results: Search engine results
        company_name: Company name
        campaign_context: Campaign targeting context
        web_context: Playwright browser context
        
    Returns:
        Complete enriched profile
    """
    builder = ProfileBuilder(campaign_context)
    
    # Step 1: Prioritize search results
    prioritized = builder.prioritize_search_results(search_results, company_name)
    
    # Step 2: Select best sources to scrape
    selected_sources = builder.select_sources_to_scrape(prioritized, max_sources=5)
    
    # Step 3: Extract data from each source
    extracted_data = []
    for source in selected_sources:
        try:
            data = await builder.extract_profile_data(source, web_context)
            extracted_data.append(data)
        except Exception as e:
            logger.error(f"Failed to extract from {source['url']}: {e}")
    
    # Step 4: Synthesize into comprehensive profile
    profile = builder.synthesize_profile(extracted_data)
    
    logger.info(f"Built profile using {len(profile['sources_used'])} sources")
    logger.info(f"Found {len(profile['personalization_hooks'])} personalization hooks")
    
    return profile