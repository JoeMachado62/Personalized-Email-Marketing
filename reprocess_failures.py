#!/usr/bin/env python3
"""
Reprocess failed Sunbiz lookups using the enhanced matcher.
This script identifies companies without owner data and retries them.
"""

import asyncio
import csv
import logging
import argparse
from pathlib import Path
from typing import List, Dict
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from enhanced_sunbiz_matcher import EnhancedSunbizMatcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def identify_failures(csv_file: str) -> List[Dict]:
    """
    Identify companies that failed to get owner information.
    
    Args:
        csv_file: Path to the enriched CSV file
        
    Returns:
        List of dictionaries containing company information
    """
    failures = []
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            company_name = row.get('DEALER NAME', '').strip()
            owner_first = row.get('Owner First Name', '').strip()
            owner_last = row.get('Owner Last Name', '').strip()
            
            # If no owner data, add to failures list
            if company_name and not owner_first and not owner_last:
                failures.append(row)
    
    return failures


async def reprocess_with_enhanced_matcher(failures: List[Dict], limit: int = None) -> List[Dict]:
    """
    Reprocess failed companies using the enhanced matcher.
    
    Args:
        failures: List of company records that failed
        limit: Optional limit on number to process
        
    Returns:
        List of updated records
    """
    matcher = EnhancedSunbizMatcher()
    
    if limit:
        failures = failures[:limit]
    
    logger.info(f"Reprocessing {len(failures)} failed companies...")
    
    success_count = 0
    still_failed = 0
    
    for i, row in enumerate(failures, 1):
        company_name = row.get('DEALER NAME', '').strip()
        
        logger.info(f"[{i}/{len(failures)}] Reprocessing: {company_name}")
        
        try:
            # Try enhanced search with multiple strategies
            result = await matcher.search_business_enhanced(company_name)
            
            if result:
                # Extract owner information
                officers = result.get('officers', [])
                auth_persons = result.get('authorized_persons', [])
                
                # Priority: President/CEO > Manager > First officer/authorized person
                owner_found = False
                
                # Check officers
                for officer in officers:
                    title = officer.get('title', '').upper()
                    if any(t in title for t in ['PRES', 'CEO', 'OWNER', 'P']):
                        row['Owner First Name'] = officer.get('first_name', '')
                        row['Owner Last Name'] = officer.get('last_name', '')
                        owner_found = True
                        logger.info(f"  ✓ Found owner: {officer.get('full_name')} ({title})")
                        break
                
                # Check authorized persons if no officer found
                if not owner_found:
                    for person in auth_persons:
                        title = person.get('title', '').upper()
                        if any(t in title for t in ['MGR', 'MANAGER', 'MEMBER', 'OWNER']):
                            row['Owner First Name'] = person.get('first_name', '')
                            row['Owner Last Name'] = person.get('last_name', '')
                            owner_found = True
                            logger.info(f"  ✓ Found owner: {person.get('full_name')} ({title})")
                            break
                
                # Use first person if no specific title match
                if not owner_found:
                    if officers:
                        row['Owner First Name'] = officers[0].get('first_name', '')
                        row['Owner Last Name'] = officers[0].get('last_name', '')
                        owner_found = True
                        logger.info(f"  ✓ Found owner: {officers[0].get('full_name')}")
                    elif auth_persons:
                        row['Owner First Name'] = auth_persons[0].get('first_name', '')
                        row['Owner Last Name'] = auth_persons[0].get('last_name', '')
                        owner_found = True
                        logger.info(f"  ✓ Found owner: {auth_persons[0].get('full_name')}")
                
                if owner_found:
                    success_count += 1
                else:
                    still_failed += 1
                    logger.warning(f"  ✗ No owner found in Sunbiz data")
            else:
                still_failed += 1
                logger.warning(f"  ✗ Still no match found")
                
        except Exception as e:
            still_failed += 1
            logger.error(f"  ✗ Error: {e}")
        
        # Small delay to be respectful
        await asyncio.sleep(0.5)
    
    logger.info("=" * 60)
    logger.info(f"REPROCESSING COMPLETE")
    logger.info(f"Newly successful: {success_count}/{len(failures)} ({success_count/len(failures)*100:.1f}%)")
    logger.info(f"Still failed: {still_failed}/{len(failures)} ({still_failed/len(failures)*100:.1f}%)")
    logger.info("=" * 60)
    
    return failures


def save_updated_csv(original_file: str, updated_records: List[Dict], output_file: str = None):
    """
    Save the updated CSV with newly found owner information.
    
    Args:
        original_file: Path to original CSV
        updated_records: List of updated records
        output_file: Optional output file path
    """
    if not output_file:
        input_path = Path(original_file)
        output_file = str(input_path.parent / f"{input_path.stem}_reprocessed.csv")
    
    # Create mapping of updated records by a unique key
    updates = {}
    for record in updated_records:
        # Use dealer name and license number as unique key
        key = (record.get('DEALER NAME', ''), record.get('LIC NUMBER', ''))
        updates[key] = record
    
    # Read original file and update records
    all_records = []
    with open(original_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        
        for row in reader:
            key = (row.get('DEALER NAME', ''), row.get('LIC NUMBER', ''))
            if key in updates:
                # Use updated record
                all_records.append(updates[key])
            else:
                # Keep original record
                all_records.append(row)
    
    # Write updated CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_records)
    
    logger.info(f"Updated CSV saved to: {output_file}")
    return output_file


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Reprocess failed Sunbiz lookups')
    parser.add_argument(
        '--input',
        type=str,
        default='florida indepent dealers_sunbiz_enriched.csv',
        help='Input CSV file with enrichment results'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output CSV file (optional)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of records to reprocess'
    )
    parser.add_argument(
        '--use-enhanced-matcher',
        action='store_true',
        default=True,
        help='Use enhanced matching (default: True)'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test mode - process only 10 records'
    )
    
    args = parser.parse_args()
    
    if args.test:
        args.limit = 10
        logger.info("TEST MODE: Processing only 10 records")
    
    # Check if input file exists
    if not Path(args.input).exists():
        logger.error(f"Input file not found: {args.input}")
        return
    
    # Identify failures
    logger.info(f"Analyzing {args.input} for failed lookups...")
    failures = await identify_failures(args.input)
    
    if not failures:
        logger.info("No failed lookups found!")
        return
    
    logger.info(f"Found {len(failures)} companies without owner information")
    
    if args.limit:
        logger.info(f"Limiting to {args.limit} records")
    
    # Reprocess with enhanced matcher
    updated_records = await reprocess_with_enhanced_matcher(failures, args.limit)
    
    # Save updated CSV
    output_file = save_updated_csv(args.input, updated_records, args.output)
    
    # Calculate final statistics
    success_count = sum(1 for r in updated_records 
                        if r.get('Owner First Name') or r.get('Owner Last Name'))
    
    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    print(f"Total reprocessed: {len(updated_records)}")
    print(f"Newly successful: {success_count}")
    print(f"Success rate: {success_count/len(updated_records)*100:.1f}%")
    print(f"Output saved to: {output_file}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())