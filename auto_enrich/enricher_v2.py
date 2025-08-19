#!/usr/bin/env python3
"""
Enricher V2 - Main orchestrator using the new Playwright-based architecture.

This enhanced enricher coordinates the entire enrichment pipeline using:
- PersonalizationIntelligence data structure
- Playwright-based web scraping
- Multi-source data validation
- Intelligent data interpretation

Usage:
    python -m auto_enrich.enricher_v2 --input data.csv --output enriched.csv --limit 5
"""

import argparse
import asyncio
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
import pandas as pd
from datetime import datetime

# Import new modules
from .intelligent_extractor_v2 import PersonalizationIntelligence
from .unified_web_scraper import UnifiedWebScraper
from .multi_url_scraper_v2 import MultiURLScraperV2
from .intelligent_web_navigator_v2 import IntelligentWebNavigatorV2
from .intelligent_data_interpreter import PersonalizedContent
from .llm_personalization_engine import LLMPersonalizationEngine

# For search (keep existing or use MCP)
try:
    from .serper_client import SerperClient
    HAS_SERPER = True
except ImportError:
    HAS_SERPER = False

logger = logging.getLogger(__name__)


class EnrichedRecord:
    """Container for an enriched business record."""
    
    def __init__(self, idx: int, row_data: Dict[str, Any]):
        self.idx = idx
        
        # Original data
        self.company_name = str(row_data.get('company_name', row_data.get('DEALER NAME', ''))).strip()
        self.address = str(row_data.get('address', row_data.get('ADDRESS', ''))).strip()
        self.city = str(row_data.get('city', row_data.get('CITY', ''))).strip()
        self.state = str(row_data.get('state', row_data.get('STATE', 'FL'))).strip()
        self.email = str(row_data.get('email', row_data.get('EMAIL', ''))).strip()
        
        # Enriched data
        self.intelligence: Optional[PersonalizationIntelligence] = None
        self.personalized_content: Optional[PersonalizedContent] = None
        self.enrichment_status = 'pending'
        self.confidence_score = 0.0
        self.errors: List[str] = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DataFrame export."""
        # Start with ALL original data
        result = {
            'Company Name': self.company_name,
            'Address': self.address,
            'City': self.city,
            'State': self.state,
            'Original Email': self.email,
            'Enrichment Status': self.enrichment_status,
            'Confidence Score': f"{self.confidence_score:.1%}"
        }
        
        if self.intelligence:
            # Add intelligence data
            result.update({
                'Website': self.intelligence.website_url,
                'Owner Name': self.intelligence.owner_name,
                'Owner Title': self.intelligence.owner_title,
                'Owner Email': self.intelligence.owner_email,
                'Owner Phone': self.intelligence.owner_phone,
                'Years in Business': self.intelligence.years_in_business,
                'Recent Achievement': self.intelligence.recent_wins[0] if self.intelligence.recent_wins else '',
                'Community Involvement': self.intelligence.community_involvement[0] if self.intelligence.community_involvement else '',
                'Primary Services': ', '.join(self.intelligence.primary_services[:3]),
                'Data Freshness': self.intelligence.data_freshness,
                'Sources Analyzed': len(self.intelligence.sources_analyzed)
            })
        
        if self.personalized_content:
            # Add personalized content
            result.update({
                'Subject Line 1': self.personalized_content.subject_lines[0] if self.personalized_content.subject_lines else '',
                'Subject Line 2': self.personalized_content.subject_lines[1] if len(self.personalized_content.subject_lines) > 1 else '',
                'Preview Text': self.personalized_content.preview_texts[0] if self.personalized_content.preview_texts else '',
                'Opening Line': self.personalized_content.opening_lines[0] if self.personalized_content.opening_lines else '',
                'Value Proposition': self.personalized_content.value_propositions[0] if self.personalized_content.value_propositions else '',
                'Call to Action': self.personalized_content.call_to_actions[0] if self.personalized_content.call_to_actions else '',
                'Pain Points': ', '.join(self.personalized_content.pain_points_addressed[:2]),
                'Personalization Score': f"{self.personalized_content.personalization_score:.1%}"
            })
        
        if self.errors:
            result['Errors'] = '; '.join(self.errors[:2])
        
        return result


class EnricherV2:
    """
    Enhanced enricher using the new Playwright-based architecture.
    """
    
    def __init__(
        self,
        concurrent_tasks: int = 3,
        use_navigator: bool = True,
        use_multi_source: bool = True,
        campaign_context: Optional[Dict] = None
    ):
        """
        Initialize the enricher.
        
        Args:
            concurrent_tasks: Number of concurrent enrichment tasks
            use_navigator: Use intelligent web navigator for deep extraction
            use_multi_source: Use multi-source scraper for validation
            campaign_context: Campaign context for personalization
        """
        self.concurrent_tasks = concurrent_tasks
        self.use_navigator = use_navigator
        self.use_multi_source = use_multi_source
        self.campaign_context = campaign_context or self._get_default_campaign_context()
        
        # Initialize components
        self.unified_scraper = UnifiedWebScraper(use_stealth=True)
        self.multi_scraper = MultiURLScraperV2() if use_multi_source else None
        self.navigator = IntelligentWebNavigatorV2() if use_navigator else None
        # Use LLM personalization engine for true AI-powered personalization
        self.personalization_engine = LLMPersonalizationEngine(self.campaign_context)
        
        # Search client
        if HAS_SERPER:
            self.search_client = SerperClient()
        else:
            self.search_client = None
    
    def _get_default_campaign_context(self) -> Dict:
        """Get default campaign context."""
        return {
            'tone': 'professional_friendly',
            'goal': 'schedule_meeting',
            'value_proposition': 'digital_transformation',
            'industry': 'automotive',
            'sender_name': 'Digital Growth Partner',
            'sender_company': 'Growth Solutions',
            'pain_points_focus': ['website_optimization', 'lead_generation', 'online_presence'],
            'include_social_media': True
        }
    
    async def enrich_record(self, record: EnrichedRecord) -> None:
        """
        Enrich a single record with comprehensive data.
        
        Args:
            record: The record to enrich
        """
        try:
            logger.info(f"Starting enrichment for {record.company_name}")
            
            # Step 1: Build search query - try company name first
            search_query = f"{record.company_name}"
            if record.city:
                search_query += f" {record.city}"
            if record.state:
                search_query += f" {record.state}"
            
            # Also prepare address-only query as fallback
            address_query = ""
            if record.address:
                address_query = f"{record.address}"
                if record.city:
                    address_query += f" {record.city}"
                if record.state:
                    address_query += f" {record.state}"
            
            # Step 2: Search for the company (if we have search client)
            search_results = []
            if self.search_client:
                try:
                    # Try company name first
                    search_results = await self.search_client.search_business(
                        record.company_name,
                        f"{record.city} {record.state}"
                    )
                    logger.info(f"Found {len(search_results)} search results for company name")
                    
                    # If no good results and we have address, try address search
                    if len(search_results) < 3 and address_query:
                        logger.info(f"Trying address search: {address_query}")
                        address_results = await self.search_client.search(address_query)
                        if address_results:
                            search_results.extend(address_results)
                            logger.info(f"Found {len(address_results)} additional results from address search")
                except Exception as e:
                    logger.warning(f"Search failed, using direct scraping: {e}")
            else:
                # Use unified scraper's search
                search_data = await self.unified_scraper.search_web(search_query)
                if search_data['success']:
                    search_results = search_data['results']
            
            # Step 3: Use multi-source scraper if enabled
            if self.use_multi_source and search_results:
                logger.info(f"Using multi-source scraper for {record.company_name}")
                intelligence = await self.multi_scraper.scrape_multiple_sources(
                    company_name=record.company_name,
                    search_results=search_results,
                    location=f"{record.city} {record.state}",
                    campaign_context=self.campaign_context
                )
            else:
                # Use unified scraper for basic extraction
                logger.info(f"Using unified scraper for {record.company_name}")
                intelligence = await self.unified_scraper.gather_web_data(
                    company_name=record.company_name,
                    location=f"{record.city} {record.state}",
                    campaign_context=self.campaign_context,
                    max_pages=3
                )
            
            # Step 4: Use navigator for deep extraction if we have a website
            if self.use_navigator and intelligence.website_url:
                logger.info(f"Deep extraction from {intelligence.website_url}")
                nav_intelligence = await self.navigator.navigate_and_extract(
                    company_name=record.company_name,
                    website_url=intelligence.website_url,
                    campaign_context=self.campaign_context
                )
                
                # Merge navigation data with existing intelligence
                self._merge_intelligence(intelligence, nav_intelligence)
            
            # Step 5: Store intelligence
            record.intelligence = intelligence
            record.confidence_score = intelligence.extraction_confidence
            
            # Step 6: Generate personalized content using LLM
            logger.info(f"Generating LLM-powered personalized content for {record.company_name}")
            personalized = await self.personalization_engine.generate_personalized_content(intelligence)
            record.personalized_content = personalized
            
            # Step 7: Update status
            if intelligence.extraction_confidence >= 0.6:
                record.enrichment_status = 'success'
            elif intelligence.extraction_confidence >= 0.3:
                record.enrichment_status = 'partial'
            else:
                record.enrichment_status = 'low_confidence'
            
            logger.info(
                f"Enrichment complete for {record.company_name}: "
                f"status={record.enrichment_status}, "
                f"confidence={record.confidence_score:.1%}"
            )
            
        except Exception as e:
            logger.error(f"Failed to enrich {record.company_name}: {e}")
            record.errors.append(str(e))
            record.enrichment_status = 'failed'
    
    def _merge_intelligence(
        self,
        target: PersonalizationIntelligence,
        source: PersonalizationIntelligence
    ) -> None:
        """Merge intelligence data from navigation into main intelligence."""
        
        # Merge owner info (prefer non-empty)
        if not target.owner_name and source.owner_name:
            target.owner_name = source.owner_name
            target.owner_title = source.owner_title
            target.owner_email = source.owner_email
            target.owner_phone = source.owner_phone
        
        # Merge lists (extend and deduplicate)
        target.recent_announcements.extend(source.recent_announcements)
        target.recent_wins.extend(source.recent_wins)
        target.community_involvement.extend(source.community_involvement)
        target.customer_success_stories.extend(source.customer_success_stories)
        target.website_issues.extend(source.website_issues)
        target.missing_capabilities.extend(source.missing_capabilities)
        target.primary_services.extend(source.primary_services)
        target.company_values.extend(source.company_values)
        
        # Deduplicate
        target.recent_announcements = target.recent_announcements[:5]
        target.recent_wins = list(set(target.recent_wins))[:5]
        target.community_involvement = list(set(target.community_involvement))[:5]
        target.primary_services = list(set(target.primary_services))[:10]
        target.company_values = list(set(target.company_values))[:5]
        
        # Update confidence if better
        if source.extraction_confidence > target.extraction_confidence:
            target.extraction_confidence = source.extraction_confidence
        
        # Add sources
        target.sources_analyzed.extend(source.sources_analyzed)
    
    async def enrich_dataframe(
        self,
        df: pd.DataFrame,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Enrich an entire DataFrame.
        
        Args:
            df: Input DataFrame
            limit: Optional limit on number of records to process
            
        Returns:
            Enriched DataFrame
        """
        logger.info(f"Starting enrichment for {len(df)} records")
        
        # Create records
        records: List[EnrichedRecord] = []
        for idx, row in df.iterrows():
            if limit and idx >= limit:
                break
            records.append(EnrichedRecord(idx, row.to_dict()))
        
        # Process with semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.concurrent_tasks)
        
        async def process_with_semaphore(record):
            async with semaphore:
                await self.enrich_record(record)
        
        # Create tasks
        tasks = [process_with_semaphore(record) for record in records]
        
        # Process all records
        await asyncio.gather(*tasks)
        
        # Close scrapers
        await self.unified_scraper.close()
        
        # Convert to DataFrame
        enriched_data = [record.to_dict() for record in records]
        enriched_df = pd.DataFrame(enriched_data)
        
        # Log summary
        success_count = sum(1 for r in records if r.enrichment_status == 'success')
        partial_count = sum(1 for r in records if r.enrichment_status == 'partial')
        failed_count = sum(1 for r in records if r.enrichment_status == 'failed')
        
        logger.info(
            f"Enrichment complete: {success_count} success, "
            f"{partial_count} partial, {failed_count} failed"
        )
        
        return enriched_df


async def main():
    """Main entry point for command-line usage."""
    
    parser = argparse.ArgumentParser(
        description="Enrich business data using advanced web scraping and AI"
    )
    parser.add_argument("--input", required=True, help="Input CSV file path")
    parser.add_argument("--output", required=True, help="Output CSV file path")
    parser.add_argument("--limit", type=int, help="Limit number of records to process")
    parser.add_argument("--concurrency", type=int, default=3, help="Number of concurrent tasks")
    parser.add_argument("--skip-navigator", action="store_true", help="Skip deep website navigation")
    parser.add_argument("--skip-multi-source", action="store_true", help="Skip multi-source validation")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load input CSV
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        return
    
    logger.info(f"Loading input CSV: {input_path}")
    df = pd.read_csv(input_path)
    logger.info(f"Loaded {len(df)} records")
    
    # Create enricher
    enricher = EnricherV2(
        concurrent_tasks=args.concurrency,
        use_navigator=not args.skip_navigator,
        use_multi_source=not args.skip_multi_source
    )
    
    # Process DataFrame
    start_time = datetime.now()
    enriched_df = await enricher.enrich_dataframe(df, limit=args.limit)
    duration = (datetime.now() - start_time).total_seconds()
    
    # Save output
    output_path = Path(args.output)
    enriched_df.to_csv(output_path, index=False)
    logger.info(f"Saved enriched data to: {output_path}")
    
    # Print summary
    print("\n" + "="*60)
    print("ENRICHMENT SUMMARY")
    print("="*60)
    print(f"Total records: {len(enriched_df)}")
    print(f"Processing time: {duration:.1f} seconds")
    print(f"Average time per record: {duration/len(enriched_df):.1f} seconds")
    
    # Status breakdown
    status_counts = enriched_df['Enrichment Status'].value_counts()
    print("\nStatus breakdown:")
    for status, count in status_counts.items():
        print(f"  {status}: {count} ({count/len(enriched_df):.1%})")
    
    # Confidence stats
    confidence_scores = enriched_df['Confidence Score'].str.rstrip('%').astype(float) / 100
    print(f"\nAverage confidence: {confidence_scores.mean():.1%}")
    print(f"Median confidence: {confidence_scores.median():.1%}")
    
    print("\nEnrichment complete!")


if __name__ == "__main__":
    asyncio.run(main())