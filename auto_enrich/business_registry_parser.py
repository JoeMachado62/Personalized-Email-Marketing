"""
Specialized parser for business registry websites (Sunbiz.org, etc.)
Extracts owner names, addresses, and other structured data from government business registries.
"""

import re
import logging
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class BusinessRegistryParser:
    """
    Parser for extracting structured data from business registry websites.
    Specializes in Florida's Sunbiz.org but can handle other state registries.
    """
    
    def __init__(self):
        """Initialize the parser with known patterns for different registries."""
        self.registry_patterns = {
            'sunbiz.org': self._parse_sunbiz,
            'dos.myflorida.com': self._parse_sunbiz,  # Same as sunbiz
            'sos.state': self._parse_generic_sos,  # Generic Secretary of State
            'corporations': self._parse_generic_corp,
            'business.registry': self._parse_generic_registry
        }
    
    def parse(self, url: str, html_content: str) -> Dict[str, Any]:
        """
        Parse business registry content based on the URL.
        
        Args:
            url: The URL of the registry page
            html_content: The HTML content to parse
            
        Returns:
            Extracted business information
        """
        # Determine which parser to use based on URL
        parser_func = None
        for pattern, func in self.registry_patterns.items():
            if pattern in url.lower():
                parser_func = func
                break
        
        if not parser_func:
            logger.warning(f"No specific parser for {url}, using generic")
            parser_func = self._parse_generic_registry
        
        try:
            return parser_func(html_content)
        except Exception as e:
            logger.error(f"Error parsing registry content from {url}: {e}")
            return {}
    
    def _parse_sunbiz(self, html_content: str) -> Dict[str, Any]:
        """
        Parse Florida Sunbiz.org business registry pages.
        
        Sunbiz structure typically includes:
        - Filing Information section
        - Officer/Director Detail section
        - Registered Agent section
        - Annual Reports section
        """
        result = {
            'registry_type': 'Florida Sunbiz',
            'owner_info': {},
            'business_info': {},
            'officers': [],
            'registered_agent': {},
            'addresses': {}
        }
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Method 1: Look for detailSection divs (newer Sunbiz format)
            detail_sections = soup.find_all('div', class_='detailSection')
            
            for section in detail_sections:
                section_text = section.get_text(strip=True)
                
                # Extract Filing Information
                if 'Filing Information' in section_text:
                    result['business_info'].update(self._extract_sunbiz_filing_info(section))
                
                # Extract Officer/Director Information (THIS IS WHERE OWNER NAMES ARE!)
                elif 'Officer/Director Detail' in section_text or 'Officer Detail' in section_text:
                    officers = self._extract_sunbiz_officers(section)
                    result['officers'] = officers
                    
                    # Find the primary owner (President, CEO, Managing Member, etc.)
                    for officer in officers:
                        title = officer.get('title', '').upper()
                        if any(term in title for term in ['PRESIDENT', 'CEO', 'OWNER', 'MANAGING MEMBER', 'MANAGER']):
                            result['owner_info'] = {
                                'full_name': officer.get('name', ''),
                                'first_name': self._extract_first_name(officer.get('name', '')),
                                'last_name': self._extract_last_name(officer.get('name', '')),
                                'title': officer.get('title', ''),
                                'address': officer.get('address', '')
                            }
                            break
                
                # Extract Registered Agent Information
                elif 'Registered Agent' in section_text:
                    result['registered_agent'] = self._extract_sunbiz_registered_agent(section)
                
                # Extract Address Information
                elif 'Principal Address' in section_text or 'Mailing Address' in section_text:
                    addresses = self._extract_sunbiz_addresses(section)
                    result['addresses'].update(addresses)
            
            # Method 2: Look for table-based layout (older Sunbiz format)
            if not result['officers']:
                tables = soup.find_all('table')
                for table in tables:
                    table_text = table.get_text(strip=True)
                    if 'Title' in table_text and 'Name' in table_text:
                        result['officers'] = self._extract_officers_from_table(table)
                        # Extract primary owner from officers
                        for officer in result['officers']:
                            if self._is_primary_owner(officer):
                                result['owner_info'] = self._format_owner_info(officer)
                                break
            
            # Method 3: Look for span elements with specific patterns
            if not result['owner_info']:
                result['owner_info'] = self._extract_owner_from_spans(soup)
            
            # Extract status and other metadata
            status_pattern = r'Status:\s*([A-Z]+)'
            status_match = re.search(status_pattern, html_content)
            if status_match:
                result['business_info']['status'] = status_match.group(1)
            
            # Extract filing date
            date_pattern = r'Date Filed:\s*(\d{2}/\d{2}/\d{4})'
            date_match = re.search(date_pattern, html_content)
            if date_match:
                result['business_info']['filing_date'] = date_match.group(1)
            
            # Extract FEI/EIN Number
            ein_pattern = r'FEI/EIN Number:\s*(\d{2}-\d{7})'
            ein_match = re.search(ein_pattern, html_content)
            if ein_match:
                result['business_info']['ein'] = ein_match.group(1)
                
        except Exception as e:
            logger.error(f"Error parsing Sunbiz content: {e}")
        
        return result
    
    def _extract_sunbiz_officers(self, section) -> List[Dict[str, str]]:
        """Extract officer information from a Sunbiz officer section."""
        officers = []
        
        try:
            # Look for spans with specific labels
            spans = section.find_all('span')
            current_officer = {}
            
            for i, span in enumerate(spans):
                text = span.get_text(strip=True)
                
                if text == 'Title':
                    # Next span should have the title value
                    if i + 1 < len(spans):
                        current_officer['title'] = spans[i + 1].get_text(strip=True)
                
                elif text == 'Name':
                    # Next span should have the name value
                    if i + 1 < len(spans):
                        current_officer['name'] = spans[i + 1].get_text(strip=True)
                
                elif text == 'Address':
                    # Collect address lines
                    if i + 1 < len(spans):
                        address_parts = []
                        j = i + 1
                        while j < len(spans) and spans[j].get_text(strip=True) not in ['Title', 'Name', 'Address']:
                            addr_text = spans[j].get_text(strip=True)
                            if addr_text:
                                address_parts.append(addr_text)
                            j += 1
                        current_officer['address'] = ' '.join(address_parts)
                
                # When we have a complete officer record
                if 'name' in current_officer and 'title' in current_officer:
                    officers.append(current_officer.copy())
                    current_officer = {}
            
            # Also try to find officer info in divs
            divs = section.find_all('div')
            for div in divs:
                div_text = div.get_text(strip=True)
                # Pattern: "Title PRESIDENT Name JOHN DOE"
                title_name_pattern = r'Title\s+([A-Z\s]+)\s+Name\s+([A-Z\s,.-]+)'
                matches = re.findall(title_name_pattern, div_text)
                for match in matches:
                    officers.append({
                        'title': match[0].strip(),
                        'name': match[1].strip()
                    })
                    
        except Exception as e:
            logger.error(f"Error extracting officers: {e}")
        
        return officers
    
    def _extract_sunbiz_filing_info(self, section) -> Dict[str, str]:
        """Extract filing information from Sunbiz."""
        info = {}
        
        try:
            text = section.get_text()
            
            # Extract various fields using regex
            patterns = {
                'document_number': r'Document Number:\s*([A-Z0-9]+)',
                'fei_ein': r'FEI/EIN Number:\s*([\d-]+)',
                'date_filed': r'Date Filed:\s*(\d{2}/\d{2}/\d{4})',
                'state': r'State:\s*([A-Z]{2})',
                'status': r'Status:\s*([A-Z\s]+)',
                'effective_date': r'Effective Date:\s*(\d{2}/\d{2}/\d{4})',
                'corporation_name': r'Corporation Name:\s*([^\n]+)',
                'last_event': r'Last Event:\s*([^\n]+)'
            }
            
            for field, pattern in patterns.items():
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    info[field] = match.group(1).strip()
                    
        except Exception as e:
            logger.error(f"Error extracting filing info: {e}")
        
        return info
    
    def _extract_sunbiz_registered_agent(self, section) -> Dict[str, str]:
        """Extract registered agent information."""
        agent = {}
        
        try:
            text = section.get_text()
            
            # Look for registered agent name and address
            name_pattern = r'Registered Agent Name:\s*([^\n]+)'
            name_match = re.search(name_pattern, text)
            if name_match:
                agent['name'] = name_match.group(1).strip()
            
            # Extract address
            addr_pattern = r'Registered Agent Address:\s*([^\n]+(?:\n[^\n]+)*?)(?=\n\n|\nRegistered|\Z)'
            addr_match = re.search(addr_pattern, text, re.MULTILINE)
            if addr_match:
                agent['address'] = ' '.join(addr_match.group(1).strip().split('\n'))
                
        except Exception as e:
            logger.error(f"Error extracting registered agent: {e}")
        
        return agent
    
    def _extract_sunbiz_addresses(self, section) -> Dict[str, str]:
        """Extract address information."""
        addresses = {}
        
        try:
            text = section.get_text()
            
            # Principal Address
            principal_pattern = r'Principal Address:\s*([^\n]+(?:\n[^\n]+)*?)(?=\n\n|\nMailing|\Z)'
            principal_match = re.search(principal_pattern, text, re.MULTILINE)
            if principal_match:
                addresses['principal'] = ' '.join(principal_match.group(1).strip().split('\n'))
            
            # Mailing Address
            mailing_pattern = r'Mailing Address:\s*([^\n]+(?:\n[^\n]+)*?)(?=\n\n|\Z)'
            mailing_match = re.search(mailing_pattern, text, re.MULTILINE)
            if mailing_match:
                addresses['mailing'] = ' '.join(mailing_match.group(1).strip().split('\n'))
                
        except Exception as e:
            logger.error(f"Error extracting addresses: {e}")
        
        return addresses
    
    def _extract_officers_from_table(self, table) -> List[Dict[str, str]]:
        """Extract officer information from HTML table."""
        officers = []
        
        try:
            rows = table.find_all('tr')
            
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    # Look for Title and Name columns
                    cell_texts = [cell.get_text(strip=True) for cell in cells]
                    if 'Title' not in cell_texts[0] and cell_texts[0]:  # Skip header row
                        officer = {}
                        if len(cell_texts) > 0:
                            officer['title'] = cell_texts[0]
                        if len(cell_texts) > 1:
                            officer['name'] = cell_texts[1]
                        if len(cell_texts) > 2:
                            officer['address'] = ' '.join(cell_texts[2:])
                        
                        if officer.get('name'):
                            officers.append(officer)
                            
        except Exception as e:
            logger.error(f"Error extracting officers from table: {e}")
        
        return officers
    
    def _extract_owner_from_spans(self, soup) -> Dict[str, str]:
        """Fallback method to extract owner from span elements."""
        owner = {}
        
        try:
            # Look for patterns like "Name: JOHN DOE"
            all_text = soup.get_text()
            
            # Pattern for officer names
            officer_patterns = [
                r'President[:\s]+([A-Z][A-Z\s,.-]+)',
                r'CEO[:\s]+([A-Z][A-Z\s,.-]+)',
                r'Managing Member[:\s]+([A-Z][A-Z\s,.-]+)',
                r'Manager[:\s]+([A-Z][A-Z\s,.-]+)',
                r'Owner[:\s]+([A-Z][A-Z\s,.-]+)',
                r'Director[:\s]+([A-Z][A-Z\s,.-]+)'
            ]
            
            for pattern in officer_patterns:
                match = re.search(pattern, all_text)
                if match:
                    name = match.group(1).strip()
                    owner = {
                        'full_name': name,
                        'first_name': self._extract_first_name(name),
                        'last_name': self._extract_last_name(name)
                    }
                    break
                    
        except Exception as e:
            logger.error(f"Error extracting owner from spans: {e}")
        
        return owner
    
    def _is_primary_owner(self, officer: Dict[str, str]) -> bool:
        """Determine if an officer is likely the primary owner."""
        primary_titles = [
            'PRESIDENT', 'CEO', 'CHIEF EXECUTIVE',
            'OWNER', 'MANAGING MEMBER', 'MANAGING PARTNER',
            'GENERAL PARTNER', 'PRINCIPAL', 'MANAGER'
        ]
        
        title = officer.get('title', '').upper()
        return any(term in title for term in primary_titles)
    
    def _format_owner_info(self, officer: Dict[str, str]) -> Dict[str, str]:
        """Format officer information into owner info structure."""
        name = officer.get('name', '')
        return {
            'full_name': name,
            'first_name': self._extract_first_name(name),
            'last_name': self._extract_last_name(name),
            'title': officer.get('title', ''),
            'address': officer.get('address', '')
        }
    
    def _extract_first_name(self, full_name: str) -> str:
        """Extract first name from full name."""
        if not full_name:
            return ''
        
        # Remove common suffixes
        name = re.sub(r'\s+(JR|SR|III|II|IV)\.?$', '', full_name, flags=re.IGNORECASE)
        
        # Handle "LAST, FIRST MIDDLE" format
        if ',' in name:
            parts = name.split(',')
            if len(parts) > 1:
                first_parts = parts[1].strip().split()
                return first_parts[0] if first_parts else ''
        
        # Handle "FIRST MIDDLE LAST" format
        parts = name.strip().split()
        return parts[0] if parts else ''
    
    def _extract_last_name(self, full_name: str) -> str:
        """Extract last name from full name."""
        if not full_name:
            return ''
        
        # Remove common suffixes
        name = re.sub(r'\s+(JR|SR|III|II|IV)\.?$', '', full_name, flags=re.IGNORECASE)
        
        # Handle "LAST, FIRST MIDDLE" format
        if ',' in name:
            parts = name.split(',')
            return parts[0].strip()
        
        # Handle "FIRST MIDDLE LAST" format
        parts = name.strip().split()
        return parts[-1] if parts else ''
    
    def _parse_generic_sos(self, html_content: str) -> Dict[str, Any]:
        """Parse generic Secretary of State pages."""
        # This would be expanded for other states
        return self._parse_generic_registry(html_content)
    
    def _parse_generic_corp(self, html_content: str) -> Dict[str, Any]:
        """Parse generic corporation registry pages."""
        return self._parse_generic_registry(html_content)
    
    def _parse_generic_registry(self, html_content: str) -> Dict[str, Any]:
        """Generic parser for any business registry."""
        result = {
            'registry_type': 'Generic',
            'owner_info': {},
            'business_info': {},
            'officers': []
        }
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            text = soup.get_text()
            
            # Look for common patterns
            patterns = {
                'status': r'Status[:\s]+([A-Za-z\s]+)',
                'formed': r'(?:Formed|Filed|Incorporated)[:\s]+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
                'type': r'(?:Entity Type|Business Type)[:\s]+([^\n]+)',
                'id': r'(?:Entity ID|File Number|Document Number)[:\s]+([A-Z0-9-]+)'
            }
            
            for field, pattern in patterns.items():
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    result['business_info'][field] = match.group(1).strip()
            
            # Look for owner/officer names
            owner_patterns = [
                r'(?:President|CEO|Owner|Manager)[:\s]+([A-Za-z\s,.-]+)',
                r'(?:Registered Agent)[:\s]+([A-Za-z\s,.-]+)',
                r'(?:Principal|Member)[:\s]+([A-Za-z\s,.-]+)'
            ]
            
            for pattern in owner_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    name = match.strip()
                    if len(name) > 3 and len(name) < 50:  # Basic validation
                        result['officers'].append({'name': name})
                        if not result['owner_info']:
                            result['owner_info'] = {
                                'full_name': name,
                                'first_name': self._extract_first_name(name),
                                'last_name': self._extract_last_name(name)
                            }
                            
        except Exception as e:
            logger.error(f"Error in generic parser: {e}")
        
        return result