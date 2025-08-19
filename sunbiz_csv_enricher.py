#!/usr/bin/env python3
"""
Standalone script to enrich Florida dealer CSV with owner names from Sunbiz.org
This script uses the existing SunbizScraper to look up each company and add owner information.
"""

import asyncio
import csv
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add the project root to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

# Use the fixed scraper from the patch file
from patch_sunbiz_scraper import SunbizScraperFixed as SunbizScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def is_likely_address(text: str) -> bool:
    """
    Check if a text string is likely an address rather than a person's name.
    
    Args:
        text: String to check
        
    Returns:
        True if likely an address, False otherwise
    """
    if not text:
        return False
    
    text_upper = text.upper()
    
    # Common address indicators
    address_indicators = [
        'AVE', 'AVENUE', 'ST', 'STREET', 'RD', 'ROAD', 'BLVD', 'BOULEVARD',
        'DR', 'DRIVE', 'LN', 'LANE', 'CT', 'COURT', 'WAY', 'PKWY', 'PARKWAY',
        'PLAZA', 'CIRCLE', 'PLACE', 'TERR', 'TERRACE', 'TRAIL', 'HWY', 'HIGHWAY',
        'SUITE', 'STE', 'APT', 'UNIT', 'NW', 'NE', 'SW', 'SE', 'NORTH', 'SOUTH',
        'EAST', 'WEST'
    ]
    
    # Check for address indicators
    for indicator in address_indicators:
        if f' {indicator}' in text_upper or text_upper.endswith(f' {indicator}'):
            return True
    
    # Check if starts with a number (common for addresses)
    if text and text[0].isdigit():
        return True
    
    return False


def extract_owner_from_sunbiz_data(sunbiz_data: Dict) -> Dict[str, str]:
    """
    Extract the most likely owner from Sunbiz data.
    
    Priority:
    1. Look for President, CEO, Owner titles in officers (skip if address)
    2. Look for Manager, Managing Member in authorized persons (skip if address)
    3. Take the first valid officer/authorized person if no clear owner title
    
    Args:
        sunbiz_data: Dictionary from SunbizScraper
        
    Returns:
        Dictionary with owner_first_name and owner_last_name
    """
    owner = {
        'owner_first_name': '',
        'owner_last_name': ''
    }
    
    if not sunbiz_data:
        return owner
    
    # Priority titles that indicate ownership
    owner_titles = ['PRES', 'PRESIDENT', 'CEO', 'OWNER', 'PRINCIPAL', 'P']
    manager_titles = ['MGR', 'MGRM', 'MANAGER', 'MANAGING MEMBER', 'MEMBER']
    
    # Check officers first (corporations)
    officers = sunbiz_data.get('officers', [])
    for officer in officers:
        title = officer.get('title', '').upper()
        full_name = officer.get('full_name', '')
        
        # Skip if this looks like an address
        if is_likely_address(full_name):
            logger.warning(f"Skipping officer that appears to be an address: {full_name}")
            continue
        
        if any(owner_title in title for owner_title in owner_titles):
            owner['owner_first_name'] = officer.get('first_name', '')
            owner['owner_last_name'] = officer.get('last_name', '')
            logger.info(f"Found owner from officers: {full_name} ({title})")
            return owner
    
    # Check authorized persons (LLCs)
    auth_persons = sunbiz_data.get('authorized_persons', [])
    for person in auth_persons:
        title = person.get('title', '').upper()
        full_name = person.get('full_name', '')
        
        # Skip if this looks like an address
        if is_likely_address(full_name):
            logger.warning(f"Skipping authorized person that appears to be an address: {full_name}")
            continue
        
        if any(manager_title in title for manager_title in manager_titles):
            owner['owner_first_name'] = person.get('first_name', '')
            owner['owner_last_name'] = person.get('last_name', '')
            logger.info(f"Found owner from authorized persons: {full_name} ({title})")
            return owner
    
    # If no clear owner title, take the first valid (non-address) officer or authorized person
    for officer in officers:
        full_name = officer.get('full_name', '')
        if not is_likely_address(full_name):
            owner['owner_first_name'] = officer.get('first_name', '')
            owner['owner_last_name'] = officer.get('last_name', '')
            logger.info(f"Using first valid officer as owner: {full_name}")
            return owner
    
    for person in auth_persons:
        full_name = person.get('full_name', '')
        if not is_likely_address(full_name):
            owner['owner_first_name'] = person.get('first_name', '')
            owner['owner_last_name'] = person.get('last_name', '')
            logger.info(f"Using first valid authorized person as owner: {full_name}")
            return owner
    
    return owner


async def process_csv_with_sunbiz(input_file: str, output_file: str = None):
    """
    Process a CSV file and add owner names from Sunbiz.
    
    Args:
        input_file: Path to input CSV
        output_file: Path to output CSV (defaults to input_file with _enriched suffix)
    """
    if not output_file:
        input_path = Path(input_file)
        output_file = str(input_path.parent / f"{input_path.stem}_sunbiz_enriched.csv")
    
    # Initialize the scraper
    scraper = SunbizScraper()
    
    # Read the CSV
    rows = []
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames
    
    logger.info(f"Processing {len(rows)} companies from {input_file}")
    
    # Process each row
    success_count = 0
    failure_count = 0
    
    for i, row in enumerate(rows, 1):
        dealer_name = row.get('DEALER NAME', '').strip()
        
        if not dealer_name:
            logger.warning(f"Row {i}: No dealer name found, skipping")
            failure_count += 1
            continue
        
        logger.info(f"[{i}/{len(rows)}] Looking up: {dealer_name}")
        
        try:
            # Search on Sunbiz
            sunbiz_data = await scraper.search_business(dealer_name)
            
            if sunbiz_data:
                # Extract owner information
                owner_info = extract_owner_from_sunbiz_data(sunbiz_data)
                
                # Update the row
                row['Owner First Name'] = owner_info['owner_first_name']
                row['Owner Last Name'] = owner_info['owner_last_name']
                
                if owner_info['owner_first_name'] or owner_info['owner_last_name']:
                    success_count += 1
                    logger.info(f"✓ Found owner: {owner_info['owner_first_name']} {owner_info['owner_last_name']}")
                else:
                    failure_count += 1
                    logger.warning(f"✗ No owner found in Sunbiz data")
            else:
                failure_count += 1
                logger.warning(f"✗ No Sunbiz results for: {dealer_name}")
                row['Owner First Name'] = ''
                row['Owner Last Name'] = ''
                
        except Exception as e:
            failure_count += 1
            logger.error(f"✗ Error processing {dealer_name}: {e}")
            row['Owner First Name'] = ''
            row['Owner Last Name'] = ''
        
        # Add a small delay to be respectful to the server
        await asyncio.sleep(0.5)
    
    # Write the enriched CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        # Ensure Owner columns are in fieldnames if not already present
        if 'Owner First Name' not in fieldnames:
            fieldnames.append('Owner First Name')
        if 'Owner Last Name' not in fieldnames:
            fieldnames.append('Owner Last Name')
        
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    # Print summary
    logger.info("=" * 60)
    logger.info(f"✅ ENRICHMENT COMPLETE")
    logger.info(f"Success: {success_count}/{len(rows)} ({success_count/len(rows)*100:.1f}%)")
    logger.info(f"Failures: {failure_count}/{len(rows)} ({failure_count/len(rows)*100:.1f}%)")
    logger.info(f"Output saved to: {output_file}")
    logger.info("=" * 60)
    
    return output_file


async def test_single_lookup():
    """Test function to verify Sunbiz lookup works."""
    scraper = SunbizScraper()
    
    # Test with first company from CSV
    test_name = "BROADWAY AUTO BROKERS INC"
    logger.info(f"Testing lookup for: {test_name}")
    
    result = await scraper.search_business(test_name)
    
    if result:
        logger.info("✓ Sunbiz lookup successful!")
        owner_info = extract_owner_from_sunbiz_data(result)
        logger.info(f"Owner: {owner_info['owner_first_name']} {owner_info['owner_last_name']}")
        
        # Show all persons found
        logger.info(f"Officers: {len(result.get('officers', []))}")
        for officer in result.get('officers', []):
            logger.info(f"  - {officer.get('full_name')} ({officer.get('title')})")
        
        logger.info(f"Authorized Persons: {len(result.get('authorized_persons', []))}")
        for person in result.get('authorized_persons', []):
            logger.info(f"  - {person.get('full_name')} ({person.get('title')})")
    else:
        logger.error("✗ No results found")
    
    return result


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enrich CSV with Sunbiz owner data')
    parser.add_argument('--test', action='store_true', help='Run test lookup')
    parser.add_argument('--input', type=str, help='Input CSV file')
    parser.add_argument('--output', type=str, help='Output CSV file (optional)')
    parser.add_argument('--limit', type=int, help='Limit number of rows to process')
    
    args = parser.parse_args()
    
    if args.test:
        # Run test
        await test_single_lookup()
    elif args.input:
        # Process CSV
        input_file = args.input
        output_file = args.output
        
        # If limit is specified, create a temporary limited CSV
        if args.limit:
            logger.info(f"Processing only first {args.limit} rows")
            # Read limited rows
            rows = []
            with open(input_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                for i, row in enumerate(reader):
                    if i >= args.limit:
                        break
                    rows.append(row)
            
            # Write to temp file
            temp_file = f"temp_limited_{args.limit}.csv"
            with open(temp_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            
            # Process the limited file
            await process_csv_with_sunbiz(temp_file, output_file)
            
            # Clean up temp file
            Path(temp_file).unlink()
        else:
            await process_csv_with_sunbiz(input_file, output_file)
    else:
        # Default: process the Florida dealers CSV
        default_csv = "florida indepent dealers.csv"
        if Path(default_csv).exists():
            logger.info(f"Processing default file: {default_csv}")
            await process_csv_with_sunbiz(default_csv)
        else:
            logger.error(f"No input file specified and default '{default_csv}' not found")
            logger.info("Usage: python sunbiz_csv_enricher.py --input yourfile.csv")
            logger.info("   or: python sunbiz_csv_enricher.py --test")


if __name__ == "__main__":
    asyncio.run(main())