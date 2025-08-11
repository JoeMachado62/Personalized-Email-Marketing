"""
Multi-URL scraper that visits multiple search results and aggregates content.
Implements smart categorization and parallel scraping for maximum data extraction.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse
import re
from datetime import datetime

from .business_registry_parser import BusinessRegistryParser
from .enhanced_content_extractor import EnhancedContentExtractor
from .serper_client import SerperClient

logger = logging.getLogger(__name__)


class MultiURLScraper:
    """
    Advanced scraper that visits multiple URLs from search results,
    categorizes them, and aggregates content intelligently.
    """
    
    def __init__(self, max_urls_per_company: int = 10, parallel_limit: int = 3):
        """
        Initialize the multi-URL scraper.
        
        Args:
            max_urls_per_company: Maximum URLs to scrape per company
            parallel_limit: Number of URLs to scrape in parallel
        """
        self.max_urls = max_urls_per_company
        self.parallel_limit = parallel_limit
        self.registry_parser = BusinessRegistryParser()
        self.content_extractor = EnhancedContentExtractor()
        self.serper_client = SerperClient()
    
    async def scrape_company(self, company_name: str, location: str = "",
                            additional_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Main method: Search for company and scrape multiple URLs.
        
        Args:
            company_name: Name of the company
            location: Location/address
            additional_data: Additional context data
            
        Returns:
            Aggregated data from all sources
        """
        result = {
            'company_name': company_name,
            'location': location,
            'search_timestamp': datetime.utcnow().isoformat(),
            'search_results_count': 0,
            'urls_scraped': 0,
            'categorized_sources': {},
            'aggregated_content': {},
            'extracted_data': {
                'owner_info': {},
                'business_details': {},
                'contact_info': {},
                'social_media': {},
                'reviews': [],
                'news_mentions': [],
                'pain_points': [],
                'achievements': []
            },
            'confidence_score': 0.0
        }
        
        try:
            # Step 1: Search using Serper (25 results)
            logger.info(f"Searching for {company_name} {location}")
            search_results = await self.serper_client.search_business(company_name, location)
            
            if not search_results:
                logger.warning(f"No search results found for {company_name}")
                return result
            
            result['search_results_count'] = len(search_results)
            logger.info(f"Got {len(search_results)} search results")
            
            # Step 2: Categorize search results
            categorized = self._categorize_search_results(search_results, company_name)
            result['categorized_sources'] = {
                k: len(v) for k, v in categorized.items() if v
            }
            
            # Step 3: Select best URLs to scrape (prioritized)
            urls_to_scrape = self._select_urls_to_scrape(categorized)
            logger.info(f"Selected {len(urls_to_scrape)} URLs to scrape")
            
            # Step 4: Scrape URLs in parallel batches
            scraped_content = await self._parallel_scrape(urls_to_scrape)
            result['urls_scraped'] = len([c for c in scraped_content if c.get('content')])
            
            # Step 5: Process and aggregate content
            aggregated = await self._aggregate_content(scraped_content, company_name)
            result['aggregated_content'] = aggregated
            
            # Step 6: Extract structured data from aggregated content
            extracted = await self._extract_structured_data(aggregated, company_name)
            result['extracted_data'] = extracted
            
            # Step 7: Calculate confidence score
            result['confidence_score'] = self._calculate_confidence(result)
            
            logger.info(f"Completed scraping for {company_name}: {result['urls_scraped']} URLs, "
                       f"confidence: {result['confidence_score']:.2%}")
            
        except Exception as e:
            logger.error(f"Error in multi-URL scraping for {company_name}: {e}")
            result['error'] = str(e)
        
        return result
    
    def _categorize_search_results(self, search_results: List[Dict], 
                                  company_name: str) -> Dict[str, List[Dict]]:
        """
        Categorize search results by type and relevance.
        
        Categories:
        - business_registry: Government business registrations
        - company_website: Official company website
        - directories: Business directories (Yelp, YellowPages, etc.)
        - social_media: Facebook, LinkedIn, Twitter, etc.
        - reviews: Google Reviews, Yelp Reviews, etc.
        - news: News articles and press releases
        - competitors: Likely competitor sites
        - irrelevant: Clearly unrelated results
        """
        categories = {
            'business_registry': [],
            'company_website': [],
            'directories': [],
            'social_media': [],
            'reviews': [],
            'news': [],
            'competitors': [],
            'irrelevant': []
        }
        
        company_name_lower = company_name.lower()
        company_words = set(company_name_lower.split())
        
        for result in search_results:
            url = result.get('url', result.get('link', ''))
            title = result.get('title', '').lower()
            snippet = result.get('snippet', '').lower()
            
            if not url:
                continue
            
            domain = urlparse(url).netloc.lower()
            
            # Business Registry Sites (HIGHEST PRIORITY)
            if any(reg in domain for reg in ['sunbiz', 'sos.state', 'corporations', 
                                             'business.registry', 'dos.myflorida',
                                             'secretary.state', 'sos.gov']):
                categories['business_registry'].append(result)
                continue
            
            # Company Website (check domain and title)
            company_match_score = sum(1 for word in company_words if word in domain)
            if company_match_score >= 2 or (
                company_match_score >= 1 and any(word in title for word in company_words)
            ):
                categories['company_website'].append(result)
                continue
            
            # Social Media
            if any(social in domain for social in ['facebook.com', 'linkedin.com', 
                                                   'twitter.com', 'instagram.com',
                                                   'youtube.com']):
                if any(word in title + snippet for word in company_words):
                    categories['social_media'].append(result)
                continue
            
            # Business Directories
            if any(dir in domain for dir in ['yelp.com', 'yellowpages.com', 
                                             'bbb.org', 'manta.com', 'dnb.com',
                                             'chamberofcommerce.com', 'bizapedia.com',
                                             'mapquest.com', 'superpages.com']):
                categories['directories'].append(result)
                continue
            
            # Review Sites
            if any(review in domain for review in ['reviews', 'rating', 'feedback']) or \
               'review' in title or 'rating' in title:
                categories['reviews'].append(result)
                continue
            
            # News
            if any(news in domain for news in ['news', 'press', 'article', 'blog']) or \
               any(term in title for term in ['announces', 'launches', 'opens']):
                categories['news'].append(result)
                continue
            
            # Check if it's a competitor (similar business in same location)
            if 'dealer' in title or 'auto' in title or 'cars' in title:
                if not any(word in title for word in company_words):
                    categories['competitors'].append(result)
                    continue
            
            # Default: Check relevance score
            relevance_score = sum(1 for word in company_words if word in title + snippet)
            if relevance_score >= 2:
                categories['directories'].append(result)  # Likely relevant
            else:
                categories['irrelevant'].append(result)
        
        # Log categorization results
        for category, items in categories.items():
            if items:
                logger.info(f"  {category}: {len(items)} results")
        
        return categories
    
    def _select_urls_to_scrape(self, categorized: Dict[str, List[Dict]]) -> List[Dict]:
        """
        Select the best URLs to scrape based on priority and limits.
        
        Priority order:
        1. Business registries (all, up to 3)
        2. Company website (first 1-2)
        3. Major directories (up to 3)
        4. Social media (up to 2)
        5. Recent reviews (up to 2)
        6. Recent news (up to 2)
        """
        selected = []
        
        # Business registries - ALWAYS scrape these first
        selected.extend(categorized['business_registry'][:3])
        
        # Company website
        selected.extend(categorized['company_website'][:2])
        
        # Directories (prioritize major ones)
        directory_priority = ['yelp.com', 'yellowpages.com', 'bbb.org']
        prioritized_dirs = []
        other_dirs = []
        
        for dir_result in categorized['directories']:
            url = dir_result.get('url', dir_result.get('link', ''))
            if any(p in url for p in directory_priority):
                prioritized_dirs.append(dir_result)
            else:
                other_dirs.append(dir_result)
        
        selected.extend(prioritized_dirs[:2])
        selected.extend(other_dirs[:1])
        
        # Social media
        selected.extend(categorized['social_media'][:2])
        
        # Reviews
        selected.extend(categorized['reviews'][:2])
        
        # Recent news
        selected.extend(categorized['news'][:1])
        
        # Limit to max URLs
        return selected[:self.max_urls]
    
    async def _parallel_scrape(self, urls_to_scrape: List[Dict]) -> List[Dict]:
        """
        Scrape multiple URLs in parallel with rate limiting.
        
        Args:
            urls_to_scrape: List of search result dicts with URLs to scrape
            
        Returns:
            List of scraped content dictionaries
        """
        results = []
        
        # Process in batches to avoid overwhelming the system
        for i in range(0, len(urls_to_scrape), self.parallel_limit):
            batch = urls_to_scrape[i:i + self.parallel_limit]
            
            # Create tasks for parallel scraping
            tasks = []
            for item in batch:
                url = item.get('url', item.get('link', ''))
                if url:
                    tasks.append(self._scrape_single_url(url, item))
            
            # Execute batch in parallel
            if tasks:
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.warning(f"Scraping error: {result}")
                        results.append({'error': str(result)})
                    else:
                        results.append(result)
                
                # Small delay between batches
                if i + self.parallel_limit < len(urls_to_scrape):
                    await asyncio.sleep(1)
        
        return results
    
    async def _scrape_single_url(self, url: str, search_result: Dict) -> Dict:
        """
        Scrape a single URL and return structured content.
        
        Args:
            url: URL to scrape
            search_result: Original search result dict
            
        Returns:
            Scraped content with metadata
        """
        result = {
            'url': url,
            'title': search_result.get('title', ''),
            'snippet': search_result.get('snippet', ''),
            'domain': urlparse(url).netloc,
            'content': '',
            'content_length': 0,
            'extraction_method': '',
            'is_business_registry': False,
            'parsed_data': {}
        }
        
        try:
            # Extract content
            logger.info(f"Scraping: {url[:100]}...")
            content = await self.content_extractor.extract(url)
            
            if content:
                result['content'] = content.get('text', content) if isinstance(content, dict) else str(content)
                result['content_length'] = len(result['content'])
                result['extraction_method'] = content.get('method', 'unknown') if isinstance(content, dict) else 'enhanced'
                
                # Special handling for business registries
                if any(reg in url.lower() for reg in ['sunbiz', 'sos.state', 'corporations']):
                    result['is_business_registry'] = True
                    # Parse with specialized parser
                    parsed = self.registry_parser.parse(url, result['content'])
                    result['parsed_data'] = parsed
                    logger.info(f"Parsed business registry: {bool(parsed.get('owner_info'))}")
                
                logger.info(f"Scraped {result['content_length']} chars from {result['domain']}")
            else:
                logger.warning(f"No content extracted from {url}")
                
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            result['error'] = str(e)
        
        return result
    
    async def _aggregate_content(self, scraped_content: List[Dict], 
                                company_name: str) -> Dict[str, Any]:
        """
        Aggregate content from multiple sources into a unified structure.
        
        Args:
            scraped_content: List of scraped content dicts
            company_name: Company name for context
            
        Returns:
            Aggregated content organized by type
        """
        aggregated = {
            'total_content_length': 0,
            'sources_count': 0,
            'business_registry': {
                'content': '',
                'parsed_data': {},
                'source_urls': []
            },
            'company_website': {
                'content': '',
                'source_urls': []
            },
            'directories': {
                'content': '',
                'source_urls': []
            },
            'social_media': {
                'content': '',
                'source_urls': []
            },
            'reviews': {
                'content': '',
                'source_urls': []
            },
            'news': {
                'content': '',
                'source_urls': []
            },
            'combined_text': ''  # All content combined for AI processing
        }
        
        all_content_parts = []
        
        for scraped in scraped_content:
            if not scraped.get('content'):
                continue
            
            content = scraped['content']
            url = scraped['url']
            domain = scraped['domain']
            
            aggregated['total_content_length'] += len(content)
            aggregated['sources_count'] += 1
            
            # Categorize and aggregate
            if scraped.get('is_business_registry'):
                aggregated['business_registry']['content'] += f"\n\n--- From {domain} ---\n{content}"
                aggregated['business_registry']['source_urls'].append(url)
                if scraped.get('parsed_data'):
                    # Merge parsed data
                    parsed = scraped['parsed_data']
                    if parsed.get('owner_info') and not aggregated['business_registry']['parsed_data'].get('owner_info'):
                        aggregated['business_registry']['parsed_data']['owner_info'] = parsed['owner_info']
                    if parsed.get('officers'):
                        if 'officers' not in aggregated['business_registry']['parsed_data']:
                            aggregated['business_registry']['parsed_data']['officers'] = []
                        aggregated['business_registry']['parsed_data']['officers'].extend(parsed['officers'])
            
            elif any(social in domain for social in ['facebook', 'linkedin', 'twitter', 'instagram']):
                aggregated['social_media']['content'] += f"\n\n--- From {domain} ---\n{content[:2000]}"
                aggregated['social_media']['source_urls'].append(url)
            
            elif any(dir in domain for dir in ['yelp', 'yellowpages', 'bbb', 'manta']):
                aggregated['directories']['content'] += f"\n\n--- From {domain} ---\n{content[:2000]}"
                aggregated['directories']['source_urls'].append(url)
            
            elif 'review' in url.lower() or 'rating' in url.lower():
                aggregated['reviews']['content'] += f"\n\n--- From {domain} ---\n{content[:1500]}"
                aggregated['reviews']['source_urls'].append(url)
            
            elif any(news in domain for news in ['news', 'press', 'article']):
                aggregated['news']['content'] += f"\n\n--- From {domain} ---\n{content[:1500]}"
                aggregated['news']['source_urls'].append(url)
            
            else:
                # Likely company website or general directory
                if company_name.lower() in domain:
                    aggregated['company_website']['content'] += f"\n\n--- From {domain} ---\n{content[:3000]}"
                    aggregated['company_website']['source_urls'].append(url)
                else:
                    aggregated['directories']['content'] += f"\n\n--- From {domain} ---\n{content[:1500]}"
                    aggregated['directories']['source_urls'].append(url)
            
            # Add to combined text (limited per source to avoid token explosion)
            all_content_parts.append(f"[Source: {domain}]\n{content[:2500]}\n")
        
        # Create combined text for AI processing
        aggregated['combined_text'] = "\n\n".join(all_content_parts)
        
        logger.info(f"Aggregated {aggregated['sources_count']} sources, "
                   f"total content: {aggregated['total_content_length']} chars")
        
        return aggregated
    
    async def _extract_structured_data(self, aggregated: Dict[str, Any], 
                                      company_name: str) -> Dict[str, Any]:
        """
        Extract structured data from aggregated content.
        
        Args:
            aggregated: Aggregated content from multiple sources
            company_name: Company name for context
            
        Returns:
            Structured extracted data
        """
        extracted = {
            'owner_info': {},
            'business_details': {},
            'contact_info': {},
            'social_media': {},
            'reviews': [],
            'news_mentions': [],
            'pain_points': [],
            'achievements': []
        }
        
        try:
            # 1. Extract owner info (prioritize business registry)
            if aggregated['business_registry']['parsed_data'].get('owner_info'):
                extracted['owner_info'] = aggregated['business_registry']['parsed_data']['owner_info']
                logger.info(f"Found owner: {extracted['owner_info'].get('full_name')}")
            
            # 2. Extract contact info from all sources
            extracted['contact_info'] = self._extract_contact_info(aggregated['combined_text'])
            
            # 3. Extract social media handles
            extracted['social_media'] = self._extract_social_media(aggregated['social_media']['content'])
            
            # 4. Extract business details
            extracted['business_details'] = self._extract_business_details(
                aggregated['company_website']['content'] or aggregated['directories']['content']
            )
            
            # 5. Extract reviews sentiment
            if aggregated['reviews']['content']:
                extracted['reviews'] = self._extract_review_highlights(aggregated['reviews']['content'])
            
            # 6. Identify pain points (what's missing or outdated)
            extracted['pain_points'] = self._identify_pain_points(aggregated)
            
            # 7. Extract achievements
            extracted['achievements'] = self._extract_achievements(
                aggregated['company_website']['content'] + aggregated['news']['content']
            )
            
        except Exception as e:
            logger.error(f"Error extracting structured data: {e}")
        
        return extracted
    
    def _extract_contact_info(self, text: str) -> Dict[str, Any]:
        """Extract contact information from text."""
        contact = {}
        
        # Phone numbers
        phone_pattern = r'[\(]?(\d{3})[\)]?[-.\s]?(\d{3})[-.\s]?(\d{4})'
        phones = re.findall(phone_pattern, text)
        if phones:
            contact['phones'] = [f"({''.join(p)})" for p in phones[:3]]
        
        # Email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            contact['emails'] = list(set(emails[:3]))
        
        # Website URLs
        url_pattern = r'https?://(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z]{2,})'
        urls = re.findall(url_pattern, text)
        if urls:
            contact['websites'] = list(set(urls[:3]))
        
        return contact
    
    def _extract_social_media(self, social_content: str) -> Dict[str, str]:
        """Extract social media profiles."""
        social = {}
        
        # Facebook
        fb_pattern = r'facebook\.com/([a-zA-Z0-9.]+)'
        fb_match = re.search(fb_pattern, social_content)
        if fb_match:
            social['facebook'] = fb_match.group(1)
        
        # LinkedIn
        li_pattern = r'linkedin\.com/(?:company|in)/([a-zA-Z0-9-]+)'
        li_match = re.search(li_pattern, social_content)
        if li_match:
            social['linkedin'] = li_match.group(1)
        
        # Twitter/X
        tw_pattern = r'(?:twitter|x)\.com/([a-zA-Z0-9_]+)'
        tw_match = re.search(tw_pattern, social_content)
        if tw_match:
            social['twitter'] = tw_match.group(1)
        
        return social
    
    def _extract_business_details(self, content: str) -> Dict[str, Any]:
        """Extract business details from content."""
        details = {}
        
        # Years in business
        year_patterns = [
            r'(?:established|founded|since|opened)\s+(?:in\s+)?(\d{4})',
            r'(\d{4})\s+(?:establishment|founding)',
            r'(\d{2,3})\+?\s+years?\s+(?:in\s+business|of\s+experience)'
        ]
        
        for pattern in year_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                year_str = match.group(1)
                if len(year_str) == 4:  # It's a year
                    details['established_year'] = int(year_str)
                    details['years_in_business'] = datetime.now().year - int(year_str)
                else:  # It's years in business
                    details['years_in_business'] = int(year_str)
                break
        
        # Business hours
        hours_pattern = r'(?:hours?|open)\s*:?\s*([0-9]{1,2}(?::[0-9]{2})?\s*[ap]m\s*-\s*[0-9]{1,2}(?::[0-9]{2})?\s*[ap]m)'
        hours_match = re.search(hours_pattern, content, re.IGNORECASE)
        if hours_match:
            details['business_hours'] = hours_match.group(1)
        
        # Specializations (for auto dealers)
        specializations = []
        spec_keywords = ['trucks', 'suvs', 'sedans', 'luxury', 'classic', 'vintage', 
                        'sports cars', 'electric', 'hybrid', 'commercial', 'fleet']
        for keyword in spec_keywords:
            if keyword in content.lower():
                specializations.append(keyword.title())
        if specializations:
            details['specializations'] = specializations[:5]
        
        return details
    
    def _extract_review_highlights(self, review_content: str) -> List[Dict]:
        """Extract review highlights and sentiment."""
        reviews = []
        
        # Look for rating patterns
        rating_pattern = r'(\d(?:\.\d)?)\s*(?:out of\s*5|stars?|★)'
        ratings = re.findall(rating_pattern, review_content)
        
        if ratings:
            avg_rating = sum(float(r) for r in ratings) / len(ratings)
            reviews.append({
                'average_rating': round(avg_rating, 1),
                'review_count': len(ratings)
            })
        
        # Extract positive keywords
        positive_keywords = ['excellent', 'great', 'amazing', 'friendly', 'professional',
                           'honest', 'fair', 'recommended', 'best', 'quality']
        positive_found = [kw for kw in positive_keywords if kw in review_content.lower()]
        
        if positive_found:
            reviews.append({
                'positive_aspects': positive_found[:5]
            })
        
        return reviews
    
    def _identify_pain_points(self, aggregated: Dict) -> List[str]:
        """Identify potential pain points from what's missing or outdated."""
        pain_points = []
        
        # Check website content
        website_content = aggregated['company_website']['content'].lower()
        
        # Website issues
        if not website_content:
            pain_points.append("No official website found")
        else:
            if 'mobile' not in website_content and 'responsive' not in website_content:
                pain_points.append("Website may not be mobile-optimized")
            if 'inventory' not in website_content and 'browse' not in website_content:
                pain_points.append("No online inventory system detected")
            if 'appointment' not in website_content and 'schedule' not in website_content:
                pain_points.append("No online appointment scheduling")
        
        # Social media presence
        if not aggregated['social_media']['content']:
            pain_points.append("Limited social media presence")
        
        # Reviews
        if not aggregated['reviews']['content']:
            pain_points.append("Few online reviews found")
        
        # Recent updates
        if aggregated['news']['content']:
            # Check if news is recent (look for dates)
            current_year = str(datetime.now().year)
            last_year = str(datetime.now().year - 1)
            if current_year not in aggregated['news']['content'] and last_year not in aggregated['news']['content']:
                pain_points.append("No recent news or updates found")
        
        return pain_points[:5]  # Limit to top 5 pain points
    
    def _extract_achievements(self, content: str) -> List[str]:
        """Extract business achievements and accolades."""
        achievements = []
        
        # Award patterns
        award_patterns = [
            r'(?:won|received|awarded|recipient)\s+([^.]+(?:award|recognition|certificate)[^.]*)',
            r'(?:best|top)\s+(?:dealer|business|company)\s+(?:of|in)\s+[^.]+',
            r'(?:#1|number one|first place)\s+[^.]+',
            r'(?:certified|authorized)\s+(?:dealer|retailer|partner)\s+(?:for|of)\s+[^.]+',
        ]
        
        for pattern in award_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                achievement = match.strip()
                if len(achievement) < 100:  # Reasonable length
                    achievements.append(achievement)
        
        # Years in business as achievement
        year_match = re.search(r'(\d{2,3})\+?\s+years?\s+(?:in\s+business|of\s+experience)', content, re.IGNORECASE)
        if year_match:
            years = year_match.group(1)
            achievements.append(f"{years}+ years in business")
        
        # Family-owned
        if 'family owned' in content.lower() or 'family-owned' in content.lower():
            achievements.append("Family-owned business")
        
        return list(set(achievements))[:5]  # Unique, limited to 5
    
    def _calculate_confidence(self, result: Dict) -> float:
        """
        Calculate confidence score based on data completeness.
        
        Args:
            result: The complete scraping result
            
        Returns:
            Confidence score between 0 and 1
        """
        score = 0.0
        max_score = 10.0
        
        # Points for different data elements
        if result['urls_scraped'] > 0:
            score += min(result['urls_scraped'] / 5, 2.0)  # Up to 2 points for URLs scraped
        
        if result['extracted_data']['owner_info']:
            score += 2.0  # 2 points for owner info
        
        if result['extracted_data']['contact_info']:
            score += 1.0  # 1 point for contact info
        
        if result['extracted_data']['business_details']:
            score += 1.0  # 1 point for business details
        
        if result['aggregated_content'].get('company_website', {}).get('content'):
            score += 1.5  # 1.5 points for company website
        
        if result['aggregated_content'].get('business_registry', {}).get('content'):
            score += 1.5  # 1.5 points for business registry
        
        if result['extracted_data']['reviews']:
            score += 0.5  # 0.5 points for reviews
        
        if result['extracted_data']['social_media']:
            score += 0.5  # 0.5 points for social media
        
        return min(score / max_score, 1.0)