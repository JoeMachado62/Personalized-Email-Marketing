#!/usr/bin/env python3
"""
Advanced content extraction system using modern NLP and extraction libraries.
This replaces basic HTML parsing with intelligent content extraction for:
1. Sunbiz corporate records
2. Dealer websites for email personalization
3. Complex multi-page content
"""

import json
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import trafilatura
from bs4 import BeautifulSoup
import html2text
from markdownify import markdownify as md
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class ExtractedContent:
    """Structured content extracted from websites."""
    # Basic info
    title: str = ""
    main_content: str = ""
    
    # Business info
    business_name: str = ""
    owner_name: str = ""
    contact_info: Dict[str, str] = field(default_factory=dict)
    
    # For email personalization
    recent_updates: List[str] = field(default_factory=list)
    services_offered: List[str] = field(default_factory=list)
    achievements: List[str] = field(default_factory=list)
    testimonials: List[str] = field(default_factory=list)
    special_offers: List[str] = field(default_factory=list)
    
    # Metadata
    extraction_method: str = "trafilatura"
    confidence: float = 0.0
    source_url: str = ""
    raw_text: str = ""


class AdvancedContentExtractor:
    """
    Advanced extraction using multiple strategies:
    1. Trafilatura for main content extraction
    2. BeautifulSoup for structured data
    3. Pattern matching for specific fields
    4. LLM integration for complex understanding
    """
    
    def __init__(self, use_llm: bool = False):
        """Initialize the extractor."""
        self.use_llm = use_llm
        self.h2t = html2text.HTML2Text()
        self.h2t.ignore_links = False
        self.h2t.ignore_images = False
        
    def extract_from_html(self, html_content: str, url: str = "") -> ExtractedContent:
        """
        Extract structured content from HTML using multiple methods.
        
        Args:
            html_content: Raw HTML content
            url: Source URL for context
            
        Returns:
            ExtractedContent with all extracted information
        """
        result = ExtractedContent(source_url=url)
        
        # Method 1: Use trafilatura for main content
        try:
            # Extract main content
            extracted = trafilatura.extract(
                html_content,
                output_format='json',
                include_comments=False,
                include_tables=True,
                deduplicate=True,
                target_language='en'
            )
            
            if extracted:
                data = json.loads(extracted)
                result.title = data.get('title', '')
                result.main_content = data.get('text', '')
                result.raw_text = data.get('raw_text', data.get('text', ''))
                
        except Exception as e:
            logger.warning(f"Trafilatura extraction failed: {e}")
        
        # Method 2: Use BeautifulSoup for structured extraction
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Extract business name
            result.business_name = self._extract_business_name(soup, html_content)
            
            # Extract contact information
            result.contact_info = self._extract_contact_info(soup, html_content)
            
            # Extract owner/officer information (for Sunbiz)
            owner = self._extract_owner_info(soup, html_content)
            if owner:
                result.owner_name = owner
            
            # Extract content for email personalization
            result.recent_updates = self._extract_recent_updates(soup)
            result.services_offered = self._extract_services(soup)
            result.achievements = self._extract_achievements(soup)
            result.testimonials = self._extract_testimonials(soup)
            result.special_offers = self._extract_offers(soup)
            
        except Exception as e:
            logger.warning(f"BeautifulSoup extraction failed: {e}")
        
        # Method 3: Fallback to markdown conversion
        if not result.main_content:
            try:
                result.main_content = md(html_content, strip=['script', 'style'])
                result.extraction_method = "markdownify"
            except:
                result.main_content = self.h2t.handle(html_content)
                result.extraction_method = "html2text"
        
        # Calculate confidence score
        result.confidence = self._calculate_confidence(result)
        
        return result
    
    def _extract_business_name(self, soup: BeautifulSoup, html: str) -> str:
        """Extract business name from various sources."""
        
        # Check meta tags
        meta_title = soup.find('meta', property='og:site_name')
        if meta_title:
            return meta_title.get('content', '')
        
        # Check title tag
        title = soup.find('title')
        if title:
            title_text = title.get_text().strip()
            # Clean common suffixes
            title_text = re.sub(r'\s*[\|-].*$', '', title_text)
            if title_text:
                return title_text
        
        # Check h1 tags
        h1 = soup.find('h1')
        if h1:
            return h1.get_text().strip()
        
        # For Sunbiz specifically
        corp_name = soup.find('div', class_='corporationName')
        if corp_name:
            return corp_name.get_text().strip()
        
        return ""
    
    def _extract_contact_info(self, soup: BeautifulSoup, html: str) -> Dict[str, str]:
        """Extract contact information."""
        contact = {}
        
        # Phone patterns
        phone_pattern = r'(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        phones = re.findall(phone_pattern, html)
        if phones:
            contact['phone'] = phones[0]
        
        # Email patterns
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, html)
        if emails:
            contact['email'] = emails[0]
        
        # Address extraction (looking for common patterns)
        address_divs = soup.find_all('div', class_=re.compile('address', re.I))
        if address_divs:
            contact['address'] = address_divs[0].get_text().strip()
        
        # Social media
        for link in soup.find_all('a', href=True):
            href = link['href']
            if 'facebook.com' in href:
                contact['facebook'] = href
            elif 'twitter.com' in href or 'x.com' in href:
                contact['twitter'] = href
            elif 'linkedin.com' in href:
                contact['linkedin'] = href
            elif 'instagram.com' in href:
                contact['instagram'] = href
        
        return contact
    
    def _extract_owner_info(self, soup: BeautifulSoup, html: str) -> Optional[str]:
        """Extract owner/officer information (optimized for Sunbiz)."""
        
        # Look for officer/director sections
        officer_sections = soup.find_all(text=re.compile('Officer|Director|Authorized Person', re.I))
        
        for section in officer_sections:
            parent = section.parent
            if parent:
                # Look for names after titles
                text = parent.get_text()
                
                # Pattern for "Title: PRESIDENT" followed by name
                patterns = [
                    r'Title[:\s]+(?:PRESIDENT|PRES|CEO|OWNER|MGR|MANAGER).*?\n([A-Z][A-Z\s,]+)',
                    r'(?:President|CEO|Owner|Manager)[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+)',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, text, re.MULTILINE)
                    if match:
                        return match.group(1).strip()
        
        return None
    
    def _extract_recent_updates(self, soup: BeautifulSoup) -> List[str]:
        """Extract recent updates/news for personalization."""
        updates = []
        
        # Look for news/updates sections
        for section in soup.find_all(['section', 'div', 'article']):
            # Check for news-related classes or IDs
            if section.get('class'):
                classes = ' '.join(section.get('class'))
                if any(word in classes.lower() for word in ['news', 'update', 'recent', 'latest', 'announcement']):
                    # Extract headlines
                    for heading in section.find_all(['h2', 'h3', 'h4']):
                        text = heading.get_text().strip()
                        if text and len(text) < 200:
                            updates.append(text)
        
        # Look for dated content
        date_pattern = r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}'
        for text in soup.stripped_strings:
            if re.search(date_pattern, text) and len(text) < 200:
                updates.append(text)
        
        return updates[:5]  # Limit to 5 most recent
    
    def _extract_services(self, soup: BeautifulSoup) -> List[str]:
        """Extract services offered."""
        services = []
        
        # Look for services sections
        for section in soup.find_all(['section', 'div']):
            if section.get('class'):
                classes = ' '.join(section.get('class'))
                if 'service' in classes.lower():
                    # Extract list items
                    for li in section.find_all('li'):
                        text = li.get_text().strip()
                        if text and len(text) < 100:
                            services.append(text)
        
        # Look for common service keywords
        service_keywords = ['repair', 'maintenance', 'inspection', 'sales', 'financing', 
                          'warranty', 'parts', 'service', 'detail', 'custom']
        
        for text in soup.stripped_strings:
            text_lower = text.lower()
            if any(keyword in text_lower for keyword in service_keywords):
                if len(text) < 100 and text not in services:
                    services.append(text)
        
        return list(set(services))[:10]  # Unique, limit to 10
    
    def _extract_achievements(self, soup: BeautifulSoup) -> List[str]:
        """Extract achievements/awards."""
        achievements = []
        
        achievement_keywords = ['award', 'winner', 'best', 'top', 'rated', 'certified', 
                               'recognized', 'achievement', 'honor', 'excellence']
        
        for text in soup.stripped_strings:
            text_lower = text.lower()
            if any(keyword in text_lower for keyword in achievement_keywords):
                if len(text) < 150:
                    achievements.append(text)
        
        return achievements[:5]
    
    def _extract_testimonials(self, soup: BeautifulSoup) -> List[str]:
        """Extract customer testimonials."""
        testimonials = []
        
        # Look for testimonial sections
        for section in soup.find_all(['section', 'div', 'blockquote']):
            if section.get('class'):
                classes = ' '.join(section.get('class'))
                if any(word in classes.lower() for word in ['testimonial', 'review', 'feedback']):
                    text = section.get_text().strip()
                    if text and 20 < len(text) < 300:
                        testimonials.append(text)
        
        # Look for quoted text
        for quote in soup.find_all('blockquote'):
            text = quote.get_text().strip()
            if text and 20 < len(text) < 300:
                testimonials.append(text)
        
        return testimonials[:3]
    
    def _extract_offers(self, soup: BeautifulSoup) -> List[str]:
        """Extract special offers/promotions."""
        offers = []
        
        offer_keywords = ['special', 'offer', 'discount', 'save', 'promotion', 
                         'deal', 'sale', '%', '$', 'off', 'free']
        
        for text in soup.stripped_strings:
            text_lower = text.lower()
            if any(keyword in text_lower for keyword in offer_keywords):
                if len(text) < 150:
                    offers.append(text)
        
        return offers[:5]
    
    def _calculate_confidence(self, content: ExtractedContent) -> float:
        """Calculate confidence score for extraction."""
        score = 0.0
        
        # Base score from content
        if content.main_content:
            score += 0.3
        if content.business_name:
            score += 0.2
        if content.contact_info:
            score += 0.1
        if content.owner_name:
            score += 0.1
        
        # Bonus for personalization content
        if content.recent_updates:
            score += 0.1
        if content.services_offered:
            score += 0.1
        if content.achievements or content.testimonials:
            score += 0.1
        
        return min(score, 1.0)
    
    def extract_for_email_personalization(self, html_content: str, company_name: str) -> Dict[str, Any]:
        """
        Extract content specifically for email personalization.
        
        Returns structured data optimized for creating personalized emails.
        """
        content = self.extract_from_html(html_content)
        
        # Build personalization data
        personalization = {
            'company_name': content.business_name or company_name,
            'hot_buttons': [],
            'ice_breakers': [],
            'value_props': [],
            'pain_points': []
        }
        
        # Generate hot buttons from content
        if content.recent_updates:
            personalization['hot_buttons'].append(f"Recent updates: {content.recent_updates[0]}")
        
        if content.achievements:
            personalization['hot_buttons'].append(f"Achievement: {content.achievements[0]}")
        
        if content.special_offers:
            personalization['hot_buttons'].append(f"Current offer: {content.special_offers[0]}")
        
        # Generate ice breakers
        if content.recent_updates:
            personalization['ice_breakers'].append(
                f"I noticed your recent {content.recent_updates[0][:50]}..."
            )
        
        if content.achievements:
            personalization['ice_breakers'].append(
                f"Congratulations on {content.achievements[0][:50]}!"
            )
        
        if content.services_offered:
            personalization['ice_breakers'].append(
                f"I see you specialize in {', '.join(content.services_offered[:2])}"
            )
        
        # Identify potential pain points from content
        pain_keywords = ['challenge', 'difficult', 'problem', 'issue', 'struggle', 
                        'concern', 'need', 'looking for', 'seeking']
        
        for text in content.raw_text.split('.'):
            if any(keyword in text.lower() for keyword in pain_keywords):
                personalization['pain_points'].append(text.strip()[:150])
        
        return personalization


# Integration with existing code
class EnhancedWebScraper:
    """
    Enhanced web scraper that replaces basic HTML parsing with advanced extraction.
    """
    
    def __init__(self):
        self.extractor = AdvancedContentExtractor()
    
    async def scrape_and_extract(self, url: str, html_content: str = None) -> ExtractedContent:
        """
        Scrape and extract content from a URL.
        
        Args:
            url: URL to scrape
            html_content: Optional pre-fetched HTML content
            
        Returns:
            ExtractedContent with all extracted information
        """
        if not html_content:
            # Fetch HTML using existing scraper
            # This would integrate with your existing Selenium/Playwright scraper
            pass
        
        return self.extractor.extract_from_html(html_content, url)
    
    def extract_for_enrichment(self, html_content: str, company_name: str) -> Dict:
        """
        Extract content for the enrichment pipeline.
        
        This replaces the basic extraction in your current enricher.
        """
        content = self.extractor.extract_from_html(html_content)
        personalization = self.extractor.extract_for_email_personalization(html_content, company_name)
        
        return {
            'website_content': content.main_content,
            'owner_name': content.owner_name,
            'contact_info': content.contact_info,
            'email_subject_ideas': personalization['ice_breakers'][:2],
            'hot_buttons': personalization['hot_buttons'],
            'pain_points': personalization['pain_points'],
            'services': content.services_offered,
            'recent_activity': content.recent_updates,
            'extraction_confidence': content.confidence
        }


def demo_extraction():
    """Demonstrate the extraction capabilities."""
    
    extractor = AdvancedContentExtractor()
    
    # Example HTML (simplified)
    sample_html = """
    <html>
    <head><title>ABC Auto Sales - Your Trusted Dealer</title></head>
    <body>
        <h1>ABC Auto Sales</h1>
        <div class="news">
            <h2>November Special: 20% off all services!</h2>
            <p>This month only, get 20% off oil changes and inspections.</p>
        </div>
        <div class="services">
            <ul>
                <li>Full Service Auto Repair</li>
                <li>State Inspections</li>
                <li>Financing Available</li>
            </ul>
        </div>
        <div class="testimonial">
            "Best service in town! They fixed my car quickly and at a fair price." - John D.
        </div>
        <div class="contact">
            Call us: (555) 123-4567
            Email: info@abcautosales.com
        </div>
    </body>
    </html>
    """
    
    result = extractor.extract_from_html(sample_html, "http://example.com")
    
    print("=" * 60)
    print("EXTRACTED CONTENT")
    print("=" * 60)
    print(f"Business Name: {result.business_name}")
    print(f"Title: {result.title}")
    print(f"Contact: {result.contact_info}")
    print(f"Services: {result.services_offered}")
    print(f"Recent Updates: {result.recent_updates}")
    print(f"Testimonials: {result.testimonials}")
    print(f"Special Offers: {result.special_offers}")
    print(f"Confidence: {result.confidence:.2f}")
    
    # Get personalization data
    personalization = extractor.extract_for_email_personalization(sample_html, "ABC Auto")
    
    print("\n" + "=" * 60)
    print("EMAIL PERSONALIZATION DATA")
    print("=" * 60)
    print(f"Ice Breakers: {personalization['ice_breakers']}")
    print(f"Hot Buttons: {personalization['hot_buttons']}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    demo_extraction()