"""
Social Media Profile Discovery and Scraping
Searches for and extracts content from business social media profiles.
"""

import asyncio
import logging
import re
from typing import Dict, List, Any, Optional, Set
from urllib.parse import urlparse, urljoin
from datetime import datetime

from .search_with_playwright import search_with_playwright
from .enhanced_content_extractor import EnhancedContentExtractor

logger = logging.getLogger(__name__)


class SocialMediaScraper:
    """
    Discovers and scrapes social media profiles for businesses.
    """
    
    def __init__(self):
        """Initialize the social media scraper."""
        self.content_extractor = EnhancedContentExtractor()
        
        # Social media platforms to search for
        self.platforms = {
            'facebook': {
                'name': 'Facebook',
                'search_terms': ['Facebook page', 'Facebook'],
                'url_patterns': [r'facebook\.com/[^/\s]+', r'fb\.com/[^/\s]+'],
                'content_selectors': [
                    '[data-testid="post_message"]',
                    '.userContent',
                    '[data-testid="story-subtitle"]',
                    '.about-section'
                ]
            },
            'instagram': {
                'name': 'Instagram', 
                'search_terms': ['Instagram', 'Instagram account'],
                'url_patterns': [r'instagram\.com/[^/\s]+'],
                'content_selectors': [
                    'article',
                    '[data-testid="media-caption"]',
                    '.bio'
                ]
            },
            'twitter': {
                'name': 'Twitter/X',
                'search_terms': ['Twitter', 'X.com', 'X account'],
                'url_patterns': [r'twitter\.com/[^/\s]+', r'x\.com/[^/\s]+'],
                'content_selectors': [
                    '[data-testid="tweet"]',
                    '[data-testid="UserDescription"]',
                    '.bio'
                ]
            },
            'linkedin': {
                'name': 'LinkedIn Company',
                'search_terms': ['LinkedIn company', 'LinkedIn page'],
                'url_patterns': [r'linkedin\.com/company/[^/\s]+'],
                'content_selectors': [
                    '.organization-about-module',
                    '.company-description',
                    '.feed-shared-article'
                ]
            },
            'youtube': {
                'name': 'YouTube',
                'search_terms': ['YouTube channel', 'YouTube'],
                'url_patterns': [r'youtube\.com/channel/[^/\s]+', r'youtube\.com/c/[^/\s]+', r'youtube\.com/@[^/\s]+'],
                'content_selectors': [
                    '#description',
                    '.about-stats',
                    '#video-title'
                ]
            },
            'tiktok': {
                'name': 'TikTok',
                'search_terms': ['TikTok', 'TikTok account'],
                'url_patterns': [r'tiktok\.com/@[^/\s]+'],
                'content_selectors': [
                    '[data-e2e="user-bio"]',
                    '[data-e2e="video-desc"]'
                ]
            }
        }
    
    async def discover_social_profiles(self, company_name: str, location: str = "", 
                                     platforms: List[str] = None) -> Dict[str, Any]:
        """
        Discover social media profiles for a business.
        
        Args:
            company_name: Business name
            location: Business location for context
            platforms: List of platforms to search (default: all)
            
        Returns:
            Dictionary with discovered social profiles
        """
        if platforms is None:
            platforms = list(self.platforms.keys())
            
        results = {
            'company_name': company_name,
            'profiles_found': {},
            'search_summary': {
                'platforms_searched': len(platforms),
                'profiles_discovered': 0,
                'total_content_chars': 0,
                'errors': []
            },
            'discovery_time': datetime.utcnow().isoformat()
        }
        
        logger.info(f"🔍 [SOCIAL] Starting social media discovery for {company_name}")
        logger.info(f"🎯 [SOCIAL] Searching platforms: {', '.join(platforms)}")
        
        for platform in platforms:
            if platform not in self.platforms:
                logger.warning(f"⚠️ [SOCIAL] Unknown platform: {platform}")
                continue
                
            try:
                profile_info = await self._search_platform(
                    platform, company_name, location
                )
                
                if profile_info and profile_info.get('url'):
                    results['profiles_found'][platform] = profile_info
                    results['search_summary']['profiles_discovered'] += 1
                    
                    # Add content length to summary
                    content_length = len(profile_info.get('content', ''))
                    results['search_summary']['total_content_chars'] += content_length
                    
                    logger.info(f"✅ [SOCIAL] Found {platform}: {profile_info['url']} ({content_length} chars)")
                else:
                    logger.info(f"❌ [SOCIAL] No {platform} profile found")
                    
            except Exception as e:
                error_msg = f"Error searching {platform}: {str(e)}"
                results['search_summary']['errors'].append(error_msg)
                logger.error(f"❌ [SOCIAL] {error_msg}")
        
        logger.info(f"📊 [SOCIAL] Discovery complete: {results['search_summary']['profiles_discovered']} profiles found")
        return results
    
    async def _search_platform(self, platform: str, company_name: str, 
                             location: str = "") -> Optional[Dict[str, Any]]:
        """
        Search for a specific platform profile.
        
        Args:
            platform: Platform name (facebook, instagram, etc.)
            company_name: Business name
            location: Business location
            
        Returns:
            Profile information if found
        """
        platform_config = self.platforms[platform]
        
        # Build search queries
        base_query = f'"{company_name}"'
        if location:
            base_query += f' "{location}"'
            
        queries = []
        for search_term in platform_config['search_terms']:
            queries.append(f'{base_query} {search_term}')
        
        logger.debug(f"🔍 [SOCIAL] Searching {platform} with queries: {queries}")
        
        # Search with each query until we find a profile
        for query in queries:
            try:
                search_results = await search_with_playwright(
                    query, 
                    max_results=10,
                    timeout=30
                )
                
                if search_results and search_results.get('results'):
                    # Look for profile URLs in search results
                    profile_url = self._extract_profile_url(
                        search_results['results'], 
                        platform_config['url_patterns']
                    )
                    
                    if profile_url:
                        # Found a profile, now scrape it
                        profile_content = await self._scrape_profile(
                            profile_url, 
                            platform_config['content_selectors']
                        )
                        
                        return {
                            'platform': platform,
                            'platform_name': platform_config['name'],
                            'url': profile_url,
                            'content': profile_content,
                            'found_via_query': query,
                            'scraped_at': datetime.utcnow().isoformat()
                        }
                        
            except Exception as e:
                logger.debug(f"Search failed for {platform} query '{query}': {e}")
                continue
        
        return None
    
    def _extract_profile_url(self, search_results: List[Dict], 
                           url_patterns: List[str]) -> Optional[str]:
        """
        Extract social profile URL from search results using regex patterns.
        
        Args:
            search_results: List of search result dictionaries
            url_patterns: List of regex patterns to match URLs
            
        Returns:
            First matching profile URL found
        """
        for result in search_results:
            url = result.get('url', '')
            title = result.get('title', '')
            snippet = result.get('snippet', '')
            
            # Check all text fields for profile URLs
            text_to_check = f"{url} {title} {snippet}"
            
            for pattern in url_patterns:
                matches = re.findall(pattern, text_to_check, re.IGNORECASE)
                if matches:
                    # Clean up the URL and return the first match
                    profile_url = matches[0]
                    if not profile_url.startswith('http'):
                        profile_url = f"https://{profile_url}"
                    return profile_url
        
        return None
    
    async def _scrape_profile(self, profile_url: str, 
                            content_selectors: List[str]) -> str:
        """
        Scrape content from a social media profile.
        
        Args:
            profile_url: URL of the social media profile
            content_selectors: CSS selectors to extract content
            
        Returns:
            Extracted content as clean text
        """
        try:
            # Use the enhanced content extractor with Playwright fallback
            extracted_content = await self.content_extractor.extract_from_url(
                profile_url,
                additional_selectors=content_selectors,
                timeout=30
            )
            
            if extracted_content:
                # Convert HTML to clean text
                content = extracted_content.get('markdown_content', '')
                if not content:
                    content = extracted_content.get('text_content', '')
                
                # Clean and truncate content for AI processing
                content = self._clean_social_content(content)
                return content[:2000]  # Limit to 2000 chars per profile
            
        except Exception as e:
            logger.debug(f"Failed to scrape {profile_url}: {e}")
        
        return ""
    
    def _clean_social_content(self, content: str) -> str:
        """
        Clean social media content for AI processing.
        
        Args:
            content: Raw scraped content
            
        Returns:
            Cleaned content
        """
        if not content:
            return ""
            
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content)
        
        # Remove social media artifacts
        content = re.sub(r'#\w+', '', content)  # Remove hashtags
        content = re.sub(r'@\w+', '', content)  # Remove mentions
        content = re.sub(r'http\S+', '', content)  # Remove URLs
        
        # Remove excessive punctuation
        content = re.sub(r'[!]{2,}', '!', content)
        content = re.sub(r'[?]{2,}', '?', content)
        
        return content.strip()
    
    async def get_social_context_for_ai(self, company_name: str, 
                                      location: str = "",
                                      platforms: List[str] = None) -> Dict[str, Any]:
        """
        Get social media context formatted for AI content generation.
        
        Args:
            company_name: Business name
            location: Business location
            platforms: List of platforms to search
            
        Returns:
            Social media context formatted for AI
        """
        social_data = await self.discover_social_profiles(
            company_name, location, platforms
        )
        
        # Format for AI consumption
        ai_context = {
            'has_social_presence': len(social_data['profiles_found']) > 0,
            'active_platforms': list(social_data['profiles_found'].keys()),
            'social_content_summary': "",
            'platform_urls': {},
            'content_themes': [],
            'total_social_content_chars': social_data['search_summary']['total_content_chars']
        }
        
        # Combine all social content for AI analysis
        all_content = []
        for platform, profile in social_data['profiles_found'].items():
            ai_context['platform_urls'][platform] = profile['url']
            if profile.get('content'):
                all_content.append(f"[{profile['platform_name']}] {profile['content']}")
        
        if all_content:
            ai_context['social_content_summary'] = " ".join(all_content)
            
            # Extract basic themes (simple keyword extraction)
            content_text = ai_context['social_content_summary'].lower()
            common_themes = [
                'customer service', 'quality', 'community', 'family',
                'local', 'trusted', 'experienced', 'professional',
                'reliable', 'satisfaction', 'innovation', 'growth'
            ]
            
            ai_context['content_themes'] = [
                theme for theme in common_themes 
                if theme in content_text
            ][:5]  # Limit to top 5 themes
        
        return ai_context


# Convenience function for integration
async def discover_social_media(company_name: str, location: str = "", 
                              platforms: List[str] = None) -> Dict[str, Any]:
    """
    Convenience function to discover social media profiles.
    
    Args:
        company_name: Business name
        location: Business location for context
        platforms: List of platforms to search (default: all)
        
    Returns:
        Social media discovery results
    """
    scraper = SocialMediaScraper()
    return await scraper.get_social_context_for_ai(company_name, location, platforms)