#!/usr/bin/env python3
"""
Intelligent Web Navigator V2 - Playwright-based multi-page navigation.

This refactored navigator integrates with the new PersonalizationIntelligence 
architecture and uses Playwright for production-ready web scraping.

Key improvements:
- Fully integrated with PersonalizationIntelligence data structure
- Uses Playwright stealth browser from intelligent_extractor_v2
- Optimized for personalization value extraction
- Better handling of JavaScript-heavy sites
- Improved content prioritization
"""

import asyncio
import logging
import re
from typing import Dict, List, Optional, Set, Tuple, Any
from urllib.parse import urljoin, urlparse
from datetime import datetime
import trafilatura
from bs4 import BeautifulSoup

from .intelligent_extractor_v2 import (
    PersonalizationIntelligence,
    PlaywrightStealthBrowser
)

logger = logging.getLogger(__name__)


class IntelligentWebNavigatorV2:
    """
    Production-ready website navigator optimized for personalization extraction.
    """
    
    # High-value pages for personalization
    VALUABLE_PAGES = {
        'leadership': {
            'patterns': ['/about', '/team', '/leadership', '/founder', '/our-story', '/meet-'],
            'weight': 10,
            'max_pages': 2
        },
        'recent_activity': {
            'patterns': ['/news', '/blog', '/updates', '/events', '/press', '/announcements'],
            'weight': 9,
            'max_pages': 3
        },
        'social_proof': {
            'patterns': ['/testimonial', '/review', '/case-stud', '/success', '/customer'],
            'weight': 8,
            'max_pages': 2
        },
        'community': {
            'patterns': ['/community', '/charity', '/giving', '/sponsor', '/social'],
            'weight': 7,
            'max_pages': 2
        },
        'services': {
            'patterns': ['/service', '/product', '/solution', '/what-we', '/offering'],
            'weight': 6,
            'max_pages': 2
        },
        'contact': {
            'patterns': ['/contact', '/location', '/hours', '/visit'],
            'weight': 5,
            'max_pages': 1
        }
    }
    
    # Pages to avoid
    AVOID_PATTERNS = [
        r'/inventory', r'/search', r'/login', r'/register', r'/cart',
        r'/privacy', r'/terms', r'/sitemap', r'/robots.txt',
        r'\.pdf$', r'\.jpg$', r'\.png$', r'\.gif$', r'\.zip$'
    ]
    
    def __init__(self, max_pages: int = 10, max_depth: int = 2):
        """
        Initialize the navigator.
        
        Args:
            max_pages: Maximum pages to visit
            max_depth: Maximum depth to traverse from homepage
        """
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.visited_urls: Set[str] = set()
        self.browser = PlaywrightStealthBrowser()
        self.intelligence = None
    
    async def navigate_and_extract(
        self,
        company_name: str,
        website_url: str,
        campaign_context: Optional[Dict] = None
    ) -> PersonalizationIntelligence:
        """
        Navigate website and extract personalization intelligence.
        
        Args:
            company_name: Name of the company
            website_url: Company website URL
            campaign_context: Optional campaign context for targeted extraction
            
        Returns:
            PersonalizationIntelligence with comprehensive data
        """
        logger.info(f"Starting navigation for {company_name} at {website_url}")
        
        # Initialize intelligence
        self.intelligence = PersonalizationIntelligence(
            business_name=company_name,
            website_url=website_url
        )
        
        try:
            # Initialize browser
            await self.browser.initialize()
            
            # Parse base URL
            parsed = urlparse(website_url)
            self.base_domain = f"{parsed.scheme}://{parsed.netloc}"
            
            # Create initial page
            page = await self.browser.create_page_with_human_behavior()
            
            # Navigate homepage
            success = await self.browser.navigate_with_human_behavior(page, website_url)
            if not success:
                self.intelligence.website_issues.append("Failed to load website")
                return self.intelligence
            
            self.visited_urls.add(website_url)
            self.intelligence.sources_analyzed.append(website_url)
            
            # Extract homepage content and discover links
            homepage_data = await self._extract_page_data(page, website_url, 'homepage')
            
            # Process homepage content
            await self._process_page_data(homepage_data, 'homepage')
            
            # Discover valuable pages
            valuable_pages = await self._discover_valuable_pages(page, homepage_data)
            
            # Visit valuable pages in priority order
            pages_visited = 1
            for page_info in valuable_pages:
                if pages_visited >= self.max_pages:
                    break
                
                url = page_info['url']
                category = page_info['category']
                
                if url in self.visited_urls:
                    continue
                
                logger.info(f"Visiting {category} page: {url}")
                
                # Navigate to page
                success = await self.browser.navigate_with_human_behavior(page, url)
                if success:
                    # Extract and process content
                    page_data = await self._extract_page_data(page, url, category)
                    await self._process_page_data(page_data, category)
                    
                    self.visited_urls.add(url)
                    self.intelligence.sources_analyzed.append(url)
                    pages_visited += 1
                else:
                    logger.warning(f"Failed to load {url}")
            
            # Post-process intelligence
            self._finalize_intelligence()
            
        except Exception as e:
            logger.error(f"Navigation error: {e}")
            self.intelligence.website_issues.append(f"Navigation error: {str(e)}")
        finally:
            await self.browser.close()
        
        return self.intelligence
    
    async def _extract_page_data(
        self,
        page,
        url: str,
        category: str
    ) -> Dict[str, Any]:
        """Extract comprehensive data from a page."""
        data = {
            'url': url,
            'category': category,
            'html': '',
            'text': '',
            'links': [],
            'structured_data': [],
            'metadata': {}
        }
        
        try:
            # Get page content
            data['html'] = await page.content()
            
            # Get page title
            data['metadata']['title'] = await page.title()
            
            # Get meta description
            data['metadata']['description'] = await page.evaluate("""
                () => {
                    const meta = document.querySelector('meta[name="description"]');
                    return meta ? meta.content : '';
                }
            """)
            
            # Get structured data (JSON-LD)
            data['structured_data'] = await page.evaluate("""
                () => {
                    const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                    const data = [];
                    scripts.forEach(script => {
                        try {
                            data.push(JSON.parse(script.textContent));
                        } catch (e) {}
                    });
                    return data;
                }
            """)
            
            # Get all links
            data['links'] = await page.evaluate("""
                () => {
                    return Array.from(document.querySelectorAll('a[href]')).map(a => ({
                        href: a.href,
                        text: (a.textContent || '').trim(),
                        title: a.title || ''
                    }));
                }
            """)
            
            # Extract clean text using trafilatura
            if data['html']:
                extracted = trafilatura.extract(
                    data['html'],
                    output_format='json',
                    include_tables=True,
                    favor_precision=True
                )
                
                if extracted:
                    import json
                    extracted_data = json.loads(extracted)
                    data['text'] = extracted_data.get('text', '')
                    data['metadata'].update({
                        'author': extracted_data.get('author'),
                        'date': extracted_data.get('date')
                    })
            
        except Exception as e:
            logger.error(f"Error extracting data from {url}: {e}")
        
        return data
    
    async def _process_page_data(self, data: Dict, category: str):
        """Process extracted page data into PersonalizationIntelligence."""
        
        if not data or not data.get('text'):
            return
        
        text = data['text']
        structured_data = data.get('structured_data', [])
        
        # Process based on category
        if category in ['homepage', 'about', 'leadership']:
            self._extract_leadership_info(text, structured_data)
            self._extract_company_info(text, structured_data)
        
        elif category == 'recent_activity':
            self._extract_recent_activity(text, data.get('metadata', {}))
        
        elif category == 'social_proof':
            self._extract_social_proof(text)
        
        elif category == 'community':
            self._extract_community_involvement(text)
        
        elif category == 'services':
            self._extract_services(text)
        
        elif category == 'contact':
            self._extract_contact_info(text)
        
        # Always look for these high-value elements
        self._extract_achievements(text)
        self._extract_pain_points(text, data.get('html', ''))
        self._extract_values(text)
    
    def _extract_leadership_info(self, text: str, structured_data: List):
        """Extract leadership and owner information."""
        
        # Check structured data first
        for item in structured_data:
            if isinstance(item, dict):
                if item.get('@type') == 'Person':
                    name = item.get('name', '')
                    title = item.get('jobTitle', '')
                    if name:
                        self.intelligence.owner_name = name
                        self.intelligence.owner_title = title
                        self.intelligence.key_decision_makers.append({
                            'name': name,
                            'title': title,
                            'email': item.get('email', ''),
                            'phone': item.get('telephone', '')
                        })
                
                elif item.get('@type') == 'Organization':
                    founder = item.get('founder')
                    if isinstance(founder, dict):
                        self.intelligence.owner_name = founder.get('name', '')
                        self.intelligence.owner_title = 'Founder'
        
        # Pattern matching
        patterns = [
            r'(?:owner|founder|president|ceo|director)[\s:]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+),?\s+(?:owner|founder|president|ceo)',
            r'(?:founded|established|led)\s+by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)'
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                name = match.group(1).strip()
                if len(name.split()) >= 2:  # Ensure it's a full name
                    if not self.intelligence.owner_name:
                        self.intelligence.owner_name = name
                    
                    # Add to decision makers
                    self.intelligence.key_decision_makers.append({
                        'name': name,
                        'title': 'Leadership',
                        'source': 'pattern_match'
                    })
    
    def _extract_company_info(self, text: str, structured_data: List):
        """Extract company information."""
        
        # Look for tagline
        tagline_patterns = [
            r'(?:our mission|we believe|dedicated to|committed to)[:\s]+([^.]{20,100})',
            r'(?:tagline|motto)[:\s]+([^.]{10,80})'
        ]
        
        for pattern in tagline_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                self.intelligence.tagline = match.group(1).strip()
                break
        
        # Look for years in business
        year_pattern = r'(?:established|founded|since|serving\s+(?:since)?)\s+(?:in\s+)?(\d{4})'
        match = re.search(year_pattern, text, re.IGNORECASE)
        if match:
            year = int(match.group(1))
            current_year = datetime.now().year
            self.intelligence.years_in_business = current_year - year
        
        # Business philosophy
        philosophy_pattern = r'(?:we believe|our philosophy|our approach)[:\s]+([^.]{30,150})'
        match = re.search(philosophy_pattern, text, re.IGNORECASE)
        if match:
            self.intelligence.business_philosophy = match.group(1).strip()
    
    def _extract_recent_activity(self, text: str, metadata: Dict):
        """Extract recent announcements and activity."""
        
        # Date patterns
        date_patterns = [
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}',
            r'\d{1,2}[/-]\d{1,2}[/-]\d{4}'
        ]
        
        for pattern in date_patterns:
            for match in re.finditer(pattern, text):
                # Extract surrounding context
                start = max(0, match.start() - 200)
                end = min(len(text), match.end() + 200)
                context = text[start:end]
                
                # Look for announcement indicators
                if any(word in context.lower() for word in 
                       ['announce', 'launch', 'introduce', 'celebrate', 'achieve', 'expand', 'new']):
                    
                    # Extract title (usually in nearby heading or first sentence)
                    lines = context.split('\n')
                    for line in lines:
                        if 20 < len(line) < 150:
                            self.intelligence.recent_announcements.append({
                                'date': match.group(0),
                                'title': line.strip(),
                                'source': metadata.get('title', 'News')
                            })
                            break
        
        # Limit to most recent
        self.intelligence.recent_announcements = self.intelligence.recent_announcements[:5]
    
    def _extract_social_proof(self, text: str):
        """Extract testimonials and success stories."""
        
        # Look for quoted testimonials
        quote_pattern = r'"([^"]{30,300})"(?:\s*[-–—]\s*([A-Z][^,\n]{2,30}))?'
        
        for match in re.finditer(quote_pattern, text):
            quote = match.group(1)
            author = match.group(2) if match.group(2) else "Customer"
            
            # Check if positive
            positive_indicators = ['great', 'excellent', 'amazing', 'best', 'recommend',
                                 'love', 'fantastic', 'outstanding', 'exceptional', 'thank']
            
            if any(word in quote.lower() for word in positive_indicators):
                self.intelligence.customer_success_stories.append({
                    'text': quote,
                    'author': author,
                    'sentiment': 'positive'
                })
        
        # Look for ratings
        rating_pattern = r'(\d+(?:\.\d+)?)\s*(?:out of\s*5|stars?|★)'
        matches = re.findall(rating_pattern, text)
        if matches:
            ratings = [float(r) for r in matches if 0 <= float(r) <= 5]
            if ratings:
                self.intelligence.ratings_summary = {
                    'average': sum(ratings) / len(ratings),
                    'count': len(ratings)
                }
        
        # Limit testimonials
        self.intelligence.customer_success_stories = self.intelligence.customer_success_stories[:5]
    
    def _extract_community_involvement(self, text: str):
        """Extract community and charity involvement."""
        
        patterns = [
            r'(?:sponsor|support|partner with|proud to support)\s+([^,.]{10,50})',
            r'(?:donate|contribute|give back)\s+to\s+([^,.]{10,50})',
            r'(?:community|local)\s+([^,.]{10,50}(?:event|program|initiative|charity|foundation))'
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                involvement = match.group(1).strip()
                if involvement and involvement not in self.intelligence.community_involvement:
                    self.intelligence.community_involvement.append(involvement)
        
        # Limit to top items
        self.intelligence.community_involvement = self.intelligence.community_involvement[:5]
    
    def _extract_services(self, text: str):
        """Extract services and offerings."""
        
        # Service indicators
        indicators = [
            r'(?:we offer|our services include|we provide|we specialize in)[:\s]+([^.]+)',
            r'(?:services|offerings|solutions)[:\s]+([^.]+)'
        ]
        
        for pattern in indicators:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                services_text = match.group(1)
                
                # Split by common delimiters
                for delimiter in [',', ';', '•', '|', '\n']:
                    if delimiter in services_text:
                        services = [s.strip() for s in services_text.split(delimiter)]
                        self.intelligence.primary_services.extend(
                            [s for s in services if 10 < len(s) < 50]
                        )
                        break
        
        # Deduplicate
        self.intelligence.primary_services = list(set(self.intelligence.primary_services))[:10]
    
    def _extract_contact_info(self, text: str):
        """Extract contact information."""
        
        # Phone numbers
        phone_pattern = r'(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        phones = re.findall(phone_pattern, text)
        if phones and not self.intelligence.owner_phone:
            self.intelligence.owner_phone = phones[0]
        
        # Email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails and not self.intelligence.owner_email:
            # Prefer personal emails over generic ones
            for email in emails:
                if not any(generic in email.lower() for generic in 
                          ['info@', 'contact@', 'sales@', 'support@']):
                    self.intelligence.owner_email = email
                    break
            else:
                self.intelligence.owner_email = emails[0]
    
    def _extract_achievements(self, text: str):
        """Extract recent achievements and awards."""
        
        patterns = [
            r'(?:won|awarded|received|earned|achieved)\s+([^.]{15,100}(?:award|recognition|certification|achievement))',
            r'(?:named|selected as|chosen as)\s+([^.]{15,100})',
            r'(?:proud|excited|pleased)\s+to\s+(?:announce|share)\s+(?:that\s+)?(?:we\s+)?([^.]{15,100})'
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                achievement = match.group(1).strip()
                if achievement and achievement not in self.intelligence.recent_wins:
                    self.intelligence.recent_wins.append(achievement)
        
        # Limit to recent/important ones
        self.intelligence.recent_wins = self.intelligence.recent_wins[:5]
    
    def _extract_pain_points(self, text: str, html: str):
        """Identify potential pain points and missing capabilities."""
        
        # Check for website issues
        if html:
            # Mobile optimization
            if 'viewport' not in html.lower():
                self.intelligence.website_issues.append("Website not mobile-optimized")
            
            # SSL
            if self.intelligence.website_url.startswith('http://'):
                self.intelligence.website_issues.append("No SSL certificate")
            
            # Outdated copyright
            copyright_match = re.search(r'©\s*(\d{4})', html)
            if copyright_match:
                year = int(copyright_match.group(1))
                if year < datetime.now().year - 1:
                    self.intelligence.website_issues.append(f"Outdated copyright ({year})")
        
        # Check for missing capabilities
        capabilities_check = {
            'online booking': ['book online', 'schedule online', 'appointment online'],
            'e-commerce': ['shop online', 'buy online', 'add to cart'],
            'customer portal': ['customer portal', 'client login', 'member area'],
            'live chat': ['live chat', 'chat with us', 'chat support']
        }
        
        text_lower = text.lower()
        for capability, indicators in capabilities_check.items():
            if not any(indicator in text_lower for indicator in indicators):
                self.intelligence.missing_capabilities.append(f"No {capability}")
        
        # Limit lists
        self.intelligence.website_issues = self.intelligence.website_issues[:5]
        self.intelligence.missing_capabilities = self.intelligence.missing_capabilities[:5]
    
    def _extract_values(self, text: str):
        """Extract company values and culture."""
        
        # Look for values section
        values_pattern = r'(?:our values|we believe in|core values|what we stand for)[:\s]+([^.]{20,500})'
        match = re.search(values_pattern, text, re.IGNORECASE)
        
        if match:
            values_text = match.group(1)
            
            # Extract individual values
            lines = values_text.split('\n')
            for line in lines:
                line = line.strip()
                if 5 < len(line) < 50:
                    self.intelligence.company_values.append(line)
        
        # Look for specific value words
        value_words = ['integrity', 'excellence', 'innovation', 'quality', 'service',
                      'trust', 'commitment', 'respect', 'teamwork', 'customer-focused']
        
        for word in value_words:
            pattern = rf'\b{word}\b[^.]*'
            if re.search(pattern, text, re.IGNORECASE):
                if word.title() not in self.intelligence.company_values:
                    self.intelligence.company_values.append(word.title())
        
        # Limit values
        self.intelligence.company_values = self.intelligence.company_values[:5]
    
    async def _discover_valuable_pages(
        self,
        page,
        homepage_data: Dict
    ) -> List[Dict]:
        """Discover and prioritize valuable pages for extraction."""
        
        valuable_pages = []
        all_links = homepage_data.get('links', [])
        
        # Score each link
        for link in all_links:
            href = link.get('href', '')
            text = link.get('text', '').lower()
            
            # Parse URL
            parsed = urlparse(href)
            
            # Skip external links
            if parsed.netloc and parsed.netloc != urlparse(self.base_domain).netloc:
                continue
            
            # Skip avoided patterns
            if any(re.search(pattern, href.lower()) for pattern in self.AVOID_PATTERNS):
                continue
            
            # Score based on patterns
            for category, config in self.VALUABLE_PAGES.items():
                for pattern in config['patterns']:
                    if pattern in href.lower() or pattern in text:
                        valuable_pages.append({
                            'url': urljoin(self.base_domain, href),
                            'category': category,
                            'weight': config['weight'],
                            'text': text
                        })
                        break
        
        # Sort by weight (priority)
        valuable_pages.sort(key=lambda x: x['weight'], reverse=True)
        
        # Limit pages per category
        seen_categories = {}
        filtered_pages = []
        
        for page_info in valuable_pages:
            category = page_info['category']
            max_pages = self.VALUABLE_PAGES[category]['max_pages']
            
            if category not in seen_categories:
                seen_categories[category] = 0
            
            if seen_categories[category] < max_pages:
                filtered_pages.append(page_info)
                seen_categories[category] += 1
        
        return filtered_pages
    
    def _finalize_intelligence(self):
        """Finalize and enhance the intelligence data."""
        
        # Generate personalization elements
        self._generate_subject_lines()
        self._generate_ice_breakers()
        self._generate_value_propositions()
        self._generate_ctas()
        
        # Calculate confidence score
        self._calculate_confidence()
        
        # Assess data freshness
        self._assess_freshness()
    
    def _generate_subject_lines(self):
        """Generate email subject lines."""
        
        if self.intelligence.recent_announcements:
            announcement = self.intelligence.recent_announcements[0]
            self.intelligence.suggested_subject_lines.append(
                f"Re: {announcement['title'][:40]}"
            )
        
        if self.intelligence.recent_wins:
            self.intelligence.suggested_subject_lines.append(
                f"Congrats on {self.intelligence.recent_wins[0][:30]}!"
            )
        
        if self.intelligence.owner_name:
            first_name = self.intelligence.owner_name.split()[0]
            self.intelligence.suggested_subject_lines.append(
                f"{first_name}, quick question about {self.intelligence.business_name}"
            )
        
        if self.intelligence.website_issues:
            self.intelligence.suggested_subject_lines.append(
                f"Quick fix for {self.intelligence.business_name}'s website"
            )
    
    def _generate_ice_breakers(self):
        """Generate conversation ice breakers."""
        
        if self.intelligence.community_involvement:
            self.intelligence.ice_breakers.append(
                f"I really admire your support of {self.intelligence.community_involvement[0]}"
            )
        
        if self.intelligence.recent_wins:
            self.intelligence.ice_breakers.append(
                f"Congratulations on {self.intelligence.recent_wins[0]}!"
            )
        
        if self.intelligence.customer_success_stories:
            story = self.intelligence.customer_success_stories[0]
            self.intelligence.ice_breakers.append(
                f"Your customer {story['author']}'s testimonial really resonated with me"
            )
        
        if self.intelligence.company_values:
            self.intelligence.ice_breakers.append(
                f"Your commitment to {self.intelligence.company_values[0]} aligns perfectly with our approach"
            )
    
    def _generate_value_propositions(self):
        """Generate value propositions."""
        
        if self.intelligence.website_issues:
            self.intelligence.value_propositions.append(
                f"I can help modernize your digital presence and fix the {self.intelligence.website_issues[0].lower()}"
            )
        
        if self.intelligence.missing_capabilities:
            self.intelligence.value_propositions.append(
                f"Let me show you how adding {self.intelligence.missing_capabilities[0].lower()} can boost your revenue"
            )
        
        if self.intelligence.competitor_advantages:
            self.intelligence.value_propositions.append(
                "I'll help you match and exceed what your competitors are doing"
            )
    
    def _generate_ctas(self):
        """Generate call-to-action options."""
        
        self.intelligence.call_to_actions = [
            "Would you be open to a quick 15-minute call this week?",
            "Can I send you a brief case study of similar businesses we've helped?",
            "Are you available for a coffee chat on Thursday or Friday?",
            "Mind if I share a 2-minute video with specific ideas for your business?"
        ]
    
    def _calculate_confidence(self):
        """Calculate extraction confidence score."""
        score = 0.0
        
        # Core information
        if self.intelligence.business_name: score += 0.1
        if self.intelligence.owner_name: score += 0.15
        if self.intelligence.owner_email or self.intelligence.owner_phone: score += 0.1
        
        # Personalization value
        if self.intelligence.recent_announcements: score += 0.15
        if self.intelligence.recent_wins: score += 0.1
        if self.intelligence.customer_success_stories: score += 0.1
        if self.intelligence.community_involvement: score += 0.1
        if self.intelligence.website_issues or self.intelligence.missing_capabilities: score += 0.1
        if len(self.intelligence.sources_analyzed) > 3: score += 0.1
        
        self.intelligence.extraction_confidence = min(score, 1.0)
    
    def _assess_freshness(self):
        """Assess data freshness."""
        
        current_year = str(datetime.now().year)
        current_month = datetime.now().strftime('%B')
        
        # Check announcements for recency
        for announcement in self.intelligence.recent_announcements:
            date_str = announcement.get('date', '')
            if current_year in date_str:
                if current_month in date_str:
                    self.intelligence.data_freshness = "Very Fresh (current month)"
                    return
                else:
                    self.intelligence.data_freshness = "Fresh (current year)"
                    return
        
        if self.intelligence.recent_announcements:
            self.intelligence.data_freshness = "Recent (within past year)"
        else:
            self.intelligence.data_freshness = "Unknown freshness"


# Test function
async def test_navigator():
    """Test the refactored navigator."""
    
    navigator = IntelligentWebNavigatorV2(max_pages=5)
    
    intelligence = await navigator.navigate_and_extract(
        company_name="Test Auto Dealership",
        website_url="https://example-dealership.com"
    )
    
    print("\n" + "="*60)
    print("EXTRACTED INTELLIGENCE")
    print("="*60)
    
    print(f"\n🏢 Business: {intelligence.business_name}")
    print(f"🌐 Website: {intelligence.website_url}")
    print(f"👤 Owner: {intelligence.owner_name} ({intelligence.owner_title})")
    print(f"📧 Contact: {intelligence.owner_email} | {intelligence.owner_phone}")
    
    print(f"\n📰 Recent Activity:")
    for announcement in intelligence.recent_announcements[:2]:
        print(f"  - {announcement['date']}: {announcement['title']}")
    
    print(f"\n🏆 Recent Wins:")
    for win in intelligence.recent_wins[:2]:
        print(f"  - {win}")
    
    print(f"\n🤝 Community Involvement:")
    for involvement in intelligence.community_involvement[:2]:
        print(f"  - {involvement}")
    
    print(f"\n⚠️ Website Issues:")
    for issue in intelligence.website_issues[:2]:
        print(f"  - {issue}")
    
    print(f"\n📊 Quality Metrics:")
    print(f"  Confidence: {intelligence.extraction_confidence:.1%}")
    print(f"  Data Freshness: {intelligence.data_freshness}")
    print(f"  Sources Analyzed: {len(intelligence.sources_analyzed)}")
    
    print(f"\n💌 Personalization Elements:")
    print(f"  Subject Lines: {len(intelligence.suggested_subject_lines)}")
    print(f"  Ice Breakers: {len(intelligence.ice_breakers)}")
    print(f"  Value Props: {len(intelligence.value_propositions)}")
    
    return intelligence


if __name__ == "__main__":
    asyncio.run(test_navigator())