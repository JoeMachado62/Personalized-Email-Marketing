"""
Main orchestrator for enriching dealership data.

This module coordinates reading an input CSV file containing basic
dealership information, discovering missing data such as website
URLs, deriving owner names, and generating personalized marketing
copy using AI. It writes the enriched data back to a new CSV.

The enrichment pipeline executes asynchronously and uses a limited
level of concurrency to perform network-bound tasks such as web
searches and API calls. To run this module from the command line,
use the helper function provided at the bottom of the file:

    python -m auto_enrich.enricher --input path/to/input.csv --output path/to/output.csv

Before running the enrichment, ensure that you have configured
environment variables in a `.env` file (see `.env.example` for
placeholders) and installed Playwright by executing `playwright
install` once after installing the Python dependencies.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

import pandas as pd

from .web_scraper import gather_web_data
from .data_interpreter import interpret_scraped_data
from .column_handler import ColumnMapper
from .ai_enrichment import generate_email_content  # Fallback

logger = logging.getLogger(__name__)


class DealerRecord:
    """A simple dataclass-like container for a dealer row.

    The input CSV may include numerous fields; this class only
    tracks the ones relevant to enrichment. Additional fields will
    be preserved transparently in the DataFrame but not stored
    separately here.
    """

    def __init__(self, idx: int, name: str, address: str, phone: str, email: Optional[str] = None, city: str = "", state: str = ""):
        self.idx = idx
        self.name = name
        self.address = address
        self.phone = phone
        self.email = email
        # Use provided city/state or extract from address
        self.city = city or self._extract_city_from_address(address)
        self.state = state

        # Enriched fields
        self.website: Optional[str] = None
        self.owner_first_name: Optional[str] = None
        self.owner_last_name: Optional[str] = None
        self.owner_phone: Optional[str] = None
        self.owner_email: Optional[str] = None
        self.subject_line: Optional[str] = None
        self.icebreaker: Optional[str] = None
        self.hot_button: Optional[str] = None

    @staticmethod
    def _extract_city_from_address(address: str) -> str:
        """Very basic heuristic to extract city from the address string.

        Assumes addresses are formatted as 'Street, City, State ZIP'.
        If parsing fails it returns an empty string.
        """
        try:
            parts = [p.strip() for p in address.split(',')]
            # The second component is typically the city
            if len(parts) >= 2:
                return parts[1]
        except Exception:
            pass
        return ""

    def update_from_scraper(self, website: Optional[str], owner_info: Dict[str, Optional[str]] | None = None) -> None:
        """Update enriched fields using scraper results.

        Args:
            website: The discovered website URL.
            owner_info: Optional dictionary with keys 'phone', 'email', 'owner_name'.
        """
        if website:
            self.website = website
        if owner_info:
            self.owner_phone = owner_info.get('phone') or self.owner_phone
            self.owner_email = owner_info.get('email') or self.owner_email
            name = owner_info.get('owner_name')
            if name and not (self.owner_first_name and self.owner_last_name):
                # Split name into first and last on whitespace
                parts = name.split()
                if parts:
                    self.owner_first_name = parts[0]
                    if len(parts) > 1:
                        self.owner_last_name = parts[-1]

    def update_from_ai(self, subject: str, icebreaker: str, hot_button: str) -> None:
        self.subject_line = subject
        self.icebreaker = icebreaker
        self.hot_button = hot_button

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for DataFrame insertion."""
        return {
            'Website': self.website,
            'Owner First Name': self.owner_first_name,
            'Owner Last Name': self.owner_last_name,
            'Owner Phone Number': self.owner_phone,
            'Owner Email': self.owner_email,
            'Personalized Email Subject Line': self.subject_line,
            'Multi Line Personalized Email Start Ice Breaker': self.icebreaker,
            'Dealer Hot Button Topic': self.hot_button,
        }


async def _enrich_record(record: DealerRecord, concurrency_semaphore: asyncio.Semaphore, custom_prompts: dict = None) -> None:
    """Internal helper to enrich a single DealerRecord.

    This coroutine acquires a semaphore to limit concurrency during
    network operations. It first attempts to discover the website,
    then optionally extracts further contact info, and finally uses
    the AI module to generate personalized marketing copy. Any
    exceptions are logged but do not break the entire pipeline.
    """
    async with concurrency_semaphore:
        try:
            logger.info(f"Enriching record: {record.name} in {record.city}")
            
            # Step 1: Gather web data (Search + Scrape)
            logger.debug(f"Gathering web data for {record.name}")
            scraped_data = await gather_web_data(
                company_name=record.name,
                location=f"{record.address} {record.city}" if record.address else record.city,
                additional_data={
                    'city': record.city,
                    'state': record.state,
                    'phone': record.phone,
                    'email': record.email
                }
            )
            
            # Step 2: Extract factual data DIRECTLY from scraped sources (no LLM needed)
            logger.debug(f"Extracting factual data for {record.name}")
            
            # Website URL - directly from Maps/scraping
            if scraped_data.get('website_url'):
                record.website = scraped_data['website_url']
                logger.debug(f"Website found: {record.website}")
            
            # Owner information - directly from Sunbiz/scraping
            # Check multi_source_profile first (new structure)
            if scraped_data.get('multi_source_profile'):
                profile = scraped_data['multi_source_profile']
                owner_info = profile.get('owner_info', {})
                logger.debug(f"Profile owner_info: {owner_info}")
                if owner_info:
                    record.owner_first_name = owner_info.get('first_name')
                    record.owner_last_name = owner_info.get('last_name')
                    logger.info(f"Owner found from profile: {record.owner_first_name} {record.owner_last_name}")
            
            # Fallback to extracted_info (focused scraper structure)
            if not record.owner_first_name and scraped_data.get('extracted_info'):
                extracted = scraped_data['extracted_info']
                if extracted.get('owner_info'):
                    owner_info = extracted['owner_info']
                    record.owner_first_name = owner_info.get('first_name')
                    record.owner_last_name = owner_info.get('last_name')
                    logger.debug(f"Owner found from extracted: {record.owner_first_name} {record.owner_last_name}")
            
            # Contact information from scraping
            contact_info = scraped_data.get('website_data', {}).get('contact_info', {})
            if contact_info.get('emails') and not record.owner_email:
                # Try to identify owner email if we have owner first name
                if record.owner_first_name:
                    for email in contact_info['emails']:
                        if record.owner_first_name.lower() in email.lower():
                            record.owner_email = email
                            break
                if not record.owner_email:
                    record.owner_email = contact_info['emails'][0]  # Use first found
            if contact_info.get('phones') and not record.owner_phone:
                record.owner_phone = contact_info['phones'][0]
            
            # Step 3: Use AI ONLY for creative content generation
            logger.debug(f"Generating personalized content for {record.name}")
            interpreted_data = await interpret_scraped_data(scraped_data, custom_prompts)
            
            # Email content
            email_content = interpreted_data.get('generated_content', {})
            if email_content:
                subject = email_content.get('subject', {}).get('raw_response', '')
                icebreaker = email_content.get('icebreaker', {}).get('raw_response', '')
                hot_button = email_content.get('hot_button', {}).get('raw_response', '')
                record.update_from_ai(subject, icebreaker, hot_button)
            
            # Log confidence scores
            confidence = interpreted_data.get('confidence_scores', {})
            logger.info(f"Enrichment confidence for {record.name}: {confidence.get('overall', 0):.2%}")
        except Exception as exc:
            logger.error("Failed to enrich record %s: %s", record.name, exc)


async def enrich_dataframe(df: pd.DataFrame, concurrent_tasks: int = 3, mapping_file: Optional[Path] = None, custom_prompts: dict = None) -> pd.DataFrame:
    """Enrich an entire DataFrame asynchronously.

    This function iterates through the rows of the input DataFrame,
    constructs DealerRecord objects, and dispatches enrichment tasks.
    It returns a new DataFrame containing both the original data and
    the enriched fields.

    Args:
        df: The input DataFrame.
        concurrent_tasks: Maximum number of enrichment tasks to run concurrently.

    Returns:
        A DataFrame with new columns appended.
    """
    # Initialize column mapper
    mapper = ColumnMapper(mapping_file)
    
    records: List[DealerRecord] = []
    
    # Use mapper to extract data
    if mapper.mappings:
        # Use mapped columns
        for idx in range(len(df)):
            data = mapper.extract_data(df, idx)
            record = DealerRecord(
                idx=idx,
                name=data.get('company_name', ''),
                address=data.get('address', ''),
                phone=data.get('phone', ''),
                email=data.get('email'),
                city=data.get('city', ''),
                state=data.get('state', '')
            )
            records.append(record)
    else:
        # Fallback to auto-detection with common column name variations
        name_col = mapper.get_column_for_field('company_name', df) or next((c for c in df.columns if 'NAME' in c.upper()), df.columns[0])
        addr_col = mapper.get_column_for_field('address', df) or next((c for c in df.columns if 'ADDRESS' in c.upper()), 'Address')
        city_col = next((c for c in df.columns if 'CITY' in c.upper()), None)
        state_col = next((c for c in df.columns if 'STATE' in c.upper()), None)
        phone_col = mapper.get_column_for_field('phone', df) or next((c for c in df.columns if 'PHONE' in c.upper()), 'Phone')
        email_col = mapper.get_column_for_field('email', df) or next((c for c in df.columns if 'EMAIL' in c.upper()), 'Email')
        
        for idx, row in df.iterrows():
            record = DealerRecord(
                idx=idx,
                name=str(row.get(name_col, '')).strip(),
                address=str(row.get(addr_col, '')).strip(),
                city=str(row.get(city_col, '')).strip() if city_col else '',
                state=str(row.get(state_col, '')).strip() if state_col else '',
                phone=str(row.get(phone_col, '')).strip(),
                email=str(row.get(email_col, '')).strip() if pd.notna(row.get(email_col, '')) else None,
            )
            records.append(record)

    semaphore = asyncio.Semaphore(concurrent_tasks)
    tasks = [asyncio.create_task(_enrich_record(rec, semaphore, custom_prompts)) for rec in records]
    await asyncio.gather(*tasks)

    # Apply enrichment back to DataFrame using mapper
    if mapper.mappings and mapper.enrichment_targets:
        # Use mapper to apply enrichment to target columns
        for rec in records:
            enrichment_data = {
                'website': rec.website,
                'owner_first_name': rec.owner_first_name,
                'owner_last_name': rec.owner_last_name,
                'owner_email': rec.owner_email,
                'owner_phone': rec.owner_phone,
                'email_subject': rec.subject_line,
                'email_icebreaker': rec.icebreaker,
                'hot_button': rec.hot_button,
            }
            mapper.apply_enrichment(df, rec.idx, enrichment_data)
        return df
    else:
        # Original behavior - append new columns
        enrichment_data = [rec.to_dict() for rec in records]
        enrichment_df = pd.DataFrame(enrichment_data, index=df.index)
        result_df = pd.concat([df.reset_index(drop=True), enrichment_df], axis=1)
        return result_df


def main() -> None:
    """Command-line interface entry point."""
    parser = argparse.ArgumentParser(description="Enrich a CSV of dealerships with AI-generated marketing content.")
    parser.add_argument("--input", required=True, help="Path to the input CSV file.")
    parser.add_argument("--output", required=True, help="Path to write the enriched CSV file.")
    parser.add_argument("--concurrency", type=int, default=3, help="Maximum number of concurrent enrichment tasks.")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        parser.error(f"Input file {input_path} does not exist.")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    logger.info("Reading input CSV from %s", input_path)
    df = pd.read_csv(input_path)

    logger.info("Starting enrichment of %d records...", len(df))
    enriched_df = asyncio.run(enrich_dataframe(df, concurrent_tasks=args.concurrency))
    logger.info("Enrichment completed. Writing output to %s", output_path)
    enriched_df.to_csv(output_path, index=False)
    logger.info("Done.")


if __name__ == "__main__":
    main()