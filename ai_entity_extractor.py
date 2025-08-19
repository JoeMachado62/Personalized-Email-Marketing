#!/usr/bin/env python3
"""
AI-powered entity extraction using modern NLP techniques.
This demonstrates how to use LLMs for complex entity matching and extraction.

For production, you could use:
1. Google's LangExtract (https://github.com/google/langextract)
2. spaCy with custom NER models
3. Hugging Face transformers with BERT/RoBERTa
4. OpenAI/Anthropic APIs for extraction
"""

import json
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class BusinessEntity:
    """Structured representation of a business entity."""
    primary_name: str
    entity_type: Optional[str] = None
    dba_names: List[str] = None
    officers: List[Dict] = None
    confidence: float = 0.0
    source_text: str = ""
    metadata: Dict = None


class AIEntityExtractor:
    """
    AI-based entity extractor that can handle complex, unstructured text.
    
    In production, this would integrate with:
    - LangExtract for grounded extraction
    - BERT/RoBERTa for entity recognition
    - GPT/Claude for complex reasoning
    """
    
    def __init__(self, use_llm: bool = False):
        """
        Initialize the extractor.
        
        Args:
            use_llm: If True, use LLM for extraction (requires API key)
        """
        self.use_llm = use_llm
        
        # Entity patterns for rule-based fallback
        self.entity_patterns = {
            'corporation': r'\b(?:inc|incorporated|corp|corporation)\b\.?',
            'llc': r'\b(?:llc|l\.l\.c\.|limited\s+liability\s+company)\b',
            'partnership': r'\b(?:lp|llp|lllp|limited\s+partnership)\b',
            'professional': r'\b(?:pa|pc|pllc|p\.a\.|p\.c\.)\b'
        }
    
    def extract_from_html(self, html_content: str) -> BusinessEntity:
        """
        Extract business entity from raw HTML (like Sunbiz pages).
        
        This is where LangExtract would excel - it can:
        1. Parse HTML while preserving structure
        2. Ground each extraction to specific source text
        3. Handle complex layouts and nested information
        """
        # For demonstration, using regex patterns
        # In production, use LangExtract or BeautifulSoup + NLP
        
        entity = BusinessEntity(
            primary_name="",
            source_text=html_content[:500]
        )
        
        # Extract company name
        name_pattern = r'<div class="corporationName">([^<]+)</div>'
        name_match = re.search(name_pattern, html_content, re.IGNORECASE)
        if name_match:
            entity.primary_name = name_match.group(1).strip()
        
        # Extract officers
        officer_pattern = r'Title[:\s]+([A-Z]+).*?\n([^,]+,\s*[^\n]+)'
        officers = []
        for match in re.finditer(officer_pattern, html_content):
            officers.append({
                'title': match.group(1),
                'name': match.group(2).strip()
            })
        entity.officers = officers
        
        return entity
    
    def extract_with_llm(self, text: str, context: str = "") -> BusinessEntity:
        """
        Use LLM to extract structured business information.
        
        This would integrate with:
        - OpenAI's function calling
        - Anthropic's Claude
        - Google's PaLM/Gemini
        - Local models via Ollama
        """
        # This is a template for LLM-based extraction
        prompt = f"""
        Extract business entity information from the following text.
        
        Context: {context}
        
        Text: {text}
        
        Return a JSON with:
        - primary_name: The main business name
        - entity_type: LLC, INC, CORP, etc.
        - dba_names: List of "doing business as" names
        - officers: List of officers with name and title
        - confidence: Your confidence level (0-1)
        
        Focus on accuracy and include only information explicitly stated.
        """
        
        # In production, you would call the LLM API here
        # For now, return a placeholder
        if self.use_llm:
            logger.info("LLM extraction would happen here with prompt")
            # response = call_llm_api(prompt)
            # return parse_llm_response(response)
        
        # Fallback to rule-based
        return self.extract_from_text(text)
    
    def extract_from_text(self, text: str) -> BusinessEntity:
        """
        Rule-based extraction as fallback.
        """
        entity = BusinessEntity(
            primary_name="",
            source_text=text[:500]
        )
        
        # Clean text
        text_clean = ' '.join(text.split())
        
        # Extract entity type
        for entity_type, pattern in self.entity_patterns.items():
            if re.search(pattern, text_clean, re.IGNORECASE):
                entity.entity_type = entity_type.upper()
                break
        
        # Extract DBA names
        dba_pattern = r'(?:dba|d/b/a|doing business as)[:\s]+([^,\n]+)'
        dba_matches = re.finditer(dba_pattern, text_clean, re.IGNORECASE)
        entity.dba_names = [m.group(1).strip() for m in dba_matches]
        
        # Extract primary name (before DBA)
        if entity.dba_names:
            parts = re.split(r'\b(?:dba|d/b/a)\b', text_clean, flags=re.IGNORECASE)
            if parts:
                entity.primary_name = parts[0].strip()
        else:
            # Take first line or up to first comma
            lines = text.strip().split('\n')
            if lines:
                entity.primary_name = lines[0].split(',')[0].strip()
        
        # Calculate confidence based on what we found
        confidence = 0.5  # Base confidence
        if entity.entity_type:
            confidence += 0.2
        if entity.primary_name:
            confidence += 0.2
        if entity.dba_names:
            confidence += 0.1
        entity.confidence = min(confidence, 1.0)
        
        return entity
    
    def match_entities(self, entity1: BusinessEntity, entity2: BusinessEntity) -> float:
        """
        Calculate similarity between two business entities.
        
        This is where BERT-based semantic similarity would help.
        """
        score = 0.0
        
        # Compare primary names
        if entity1.primary_name and entity2.primary_name:
            # Use edit distance or semantic similarity
            # For now, simple token overlap
            tokens1 = set(entity1.primary_name.upper().split())
            tokens2 = set(entity2.primary_name.upper().split())
            if tokens1 and tokens2:
                overlap = len(tokens1 & tokens2) / len(tokens1 | tokens2)
                score += overlap * 0.5
        
        # Compare entity types
        if entity1.entity_type == entity2.entity_type:
            score += 0.2
        
        # Check DBA names
        if entity1.dba_names and entity2.dba_names:
            if set(entity1.dba_names) & set(entity2.dba_names):
                score += 0.2
        
        # Check officers
        if entity1.officers and entity2.officers:
            officer_names1 = {o.get('name', '').upper() for o in entity1.officers}
            officer_names2 = {o.get('name', '').upper() for o in entity2.officers}
            if officer_names1 & officer_names2:
                score += 0.1
        
        return min(score, 1.0)


class LangExtractIntegration:
    """
    Integration with Google's LangExtract for production use.
    
    LangExtract provides:
    1. Precise source grounding - know exactly where each fact came from
    2. Interactive visualization - see extractions highlighted in source
    3. Multi-modal support - works with text, tables, PDFs
    4. Schema validation - ensure extracted data matches expected structure
    """
    
    @staticmethod
    def create_extraction_schema():
        """
        Define the schema for business entity extraction.
        """
        schema = {
            "type": "object",
            "properties": {
                "company_name": {
                    "type": "string",
                    "description": "The official registered name of the company"
                },
                "entity_type": {
                    "type": "string",
                    "enum": ["LLC", "INC", "CORP", "LP", "LLP", "PA", "PC"],
                    "description": "The type of business entity"
                },
                "dba_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Alternative names the business operates under"
                },
                "officers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "title": {"type": "string"},
                            "address": {"type": "string"}
                        }
                    }
                },
                "registration": {
                    "type": "object",
                    "properties": {
                        "date_filed": {"type": "string", "format": "date"},
                        "status": {"type": "string"},
                        "document_number": {"type": "string"},
                        "fein": {"type": "string"}
                    }
                }
            },
            "required": ["company_name"]
        }
        return schema
    
    @staticmethod
    def extract_with_langextract(html_content: str):
        """
        Example of how to use LangExtract for extraction.
        
        In production:
        ```python
        from langextract import LangExtract
        
        extractor = LangExtract(
            model="gemini-1.5-pro",  # or gpt-4, claude-3
            schema=create_extraction_schema()
        )
        
        result = extractor.extract(
            html_content,
            instructions="Extract business registration information"
        )
        
        # Get extracted data with source grounding
        for extraction in result.extractions:
            print(f"Found: {extraction.value}")
            print(f"Source: {extraction.source_text}")
            print(f"Confidence: {extraction.confidence}")
        ```
        """
        # This would require langextract to be installed
        # pip install langextract
        pass


def demonstrate_ai_extraction():
    """
    Demonstrate AI-based extraction capabilities.
    """
    
    print("=" * 60)
    print("AI-POWERED ENTITY EXTRACTION DEMONSTRATION")
    print("=" * 60)
    
    # Example problematic text
    test_cases = [
        {
            "raw": 'G & G SALES AND SERVICE "LLC"',
            "context": "Sunbiz search result with quotes around LLC"
        },
        {
            "raw": "DEAL MAKER OF GAINESVILLE LIMITED LIABILITY COMPANY",
            "context": "Full entity name instead of abbreviation"
        },
        {
            "raw": "GAMAS CORP DBA GAMAS AUTO SALES",
            "context": "Company with DBA name"
        },
        {
            "raw": "BILLY GRACE",
            "context": "Personal name, might be sole proprietor"
        }
    ]
    
    extractor = AIEntityExtractor()
    
    for case in test_cases:
        print(f"\nInput: {case['raw']}")
        print(f"Context: {case['context']}")
        
        entity = extractor.extract_from_text(case['raw'])
        
        print(f"Extracted:")
        print(f"  Primary Name: {entity.primary_name}")
        print(f"  Entity Type: {entity.entity_type}")
        print(f"  DBA Names: {entity.dba_names}")
        print(f"  Confidence: {entity.confidence:.2f}")
    
    print("\n" + "=" * 60)
    print("BENEFITS OF AI/LLM APPROACH:")
    print("=" * 60)
    print("""
    1. HANDLES COMPLEXITY: Can understand context, variations, abbreviations
    2. SEMANTIC UNDERSTANDING: Knows "LLC" = "Limited Liability Company"
    3. FUZZY MATCHING: Can match "J.D. SANDERS" with "J D SANDERS"
    4. CONTEXT AWARE: Understands DBA, subsidiaries, parent companies
    5. SELF-IMPROVING: Can be fine-tuned on your specific data
    6. SOURCE GROUNDING: With LangExtract, know exactly where data came from
    7. MULTI-MODAL: Can extract from PDFs, images, tables, not just text
    
    For your use case, a hybrid approach would be ideal:
    - Use rule-based for simple, clear cases (90% of data)
    - Use AI/LLM for complex edge cases (10% that fail rules)
    - Use LangExtract for extracting from complex HTML/PDF documents
    """)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    demonstrate_ai_extraction()