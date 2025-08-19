#!/usr/bin/env python3
"""Analyze failed Sunbiz lookups to identify patterns."""

import csv
import re
from collections import Counter
from pathlib import Path

def analyze_failures():
    """Extract and analyze companies that failed to get owner information."""
    
    enriched_file = "florida indepent dealers_sunbiz_enriched.csv"
    
    # Read the CSV and identify failures
    failed_companies = []
    successful_companies = []
    
    with open(enriched_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            company_name = row.get('DEALER NAME', '').strip()
            owner_first = row.get('Owner First Name', '').strip()
            owner_last = row.get('Owner Last Name', '').strip()
            
            if company_name:
                if not owner_first and not owner_last:
                    failed_companies.append(company_name)
                else:
                    successful_companies.append(company_name)
    
    print(f"Total companies: {len(failed_companies) + len(successful_companies)}")
    print(f"Failed lookups: {len(failed_companies)} ({len(failed_companies)/(len(failed_companies)+len(successful_companies))*100:.1f}%)")
    print(f"Successful lookups: {len(successful_companies)}")
    
    # Analyze patterns in failed companies
    print("\n" + "="*60)
    print("PATTERN ANALYSIS OF FAILED LOOKUPS")
    print("="*60)
    
    # Pattern 1: Personal names (not business entities)
    personal_names = []
    for name in failed_companies:
        # Check if it looks like a personal name (no business suffix)
        if not any(suffix in name.upper() for suffix in ['INC', 'LLC', 'CORP', 'COMPANY', 'CO', 'LTD', 'ENTERPRISES', 'GROUP']):
            # Check if it looks like a person's name (2-4 words, no numbers)
            words = name.split()
            if 2 <= len(words) <= 4 and not any(char.isdigit() for char in name):
                personal_names.append(name)
    
    print(f"\n1. PERSONAL NAMES (not business entities): {len(personal_names)}")
    if personal_names:
        print("   Examples:")
        for name in personal_names[:10]:
            print(f"   - {name}")
    
    # Pattern 2: DBA or trade names
    dba_names = []
    for name in failed_companies:
        if 'DBA' in name.upper() or 'D/B/A' in name.upper() or 'D.B.A' in name.upper():
            dba_names.append(name)
    
    print(f"\n2. DBA (Doing Business As) names: {len(dba_names)}")
    if dba_names:
        print("   Examples:")
        for name in dba_names[:5]:
            print(f"   - {name}")
    
    # Pattern 3: Names with special characters or formatting issues
    special_char_names = []
    for name in failed_companies:
        if any(char in name for char in ['&', '/', '#', '@', '(', ')', '-', "'"]):
            special_char_names.append(name)
    
    print(f"\n3. Names with special characters: {len(special_char_names)}")
    if special_char_names:
        print("   Examples:")
        for name in special_char_names[:10]:
            print(f"   - {name}")
    
    # Pattern 4: Very long names (might be truncated in search)
    long_names = [name for name in failed_companies if len(name) > 50]
    
    print(f"\n4. Very long names (>50 chars): {len(long_names)}")
    if long_names:
        print("   Examples:")
        for name in long_names[:5]:
            print(f"   - {name[:80]}...")
    
    # Pattern 5: Names with numbers at the beginning
    number_start = [name for name in failed_companies if name and name[0].isdigit()]
    
    print(f"\n5. Names starting with numbers: {len(number_start)}")
    if number_start:
        print("   Examples:")
        for name in number_start[:10]:
            print(f"   - {name}")
    
    # Pattern 6: Common words that might indicate non-corporate entities
    non_corporate_keywords = ['AUTO', 'MOTORS', 'CARS', 'AUTOMOTIVE', 'WHOLESALE', 'SALES', 'SERVICE']
    standalone_keywords = []
    for name in failed_companies:
        name_upper = name.upper()
        # Check if name is mostly just keywords without Inc/LLC
        if any(keyword in name_upper for keyword in non_corporate_keywords):
            if not any(suffix in name_upper for suffix in ['INC', 'LLC', 'CORP']):
                standalone_keywords.append(name)
    
    print(f"\n6. Generic business names without corporate suffix: {len(set(standalone_keywords) - set(personal_names))}")
    examples = list(set(standalone_keywords) - set(personal_names))[:10]
    if examples:
        print("   Examples:")
        for name in examples:
            print(f"   - {name}")
    
    # Pattern 7: Inactive or dissolved companies
    # Check log for specific error patterns
    log_file = "sunbiz_enrichment.log"
    no_match_pattern = []
    
    if Path(log_file).exists():
        with open(log_file, 'r') as f:
            log_content = f.read()
            for name in failed_companies[:50]:  # Sample check
                if f"No exact match found for: {name}" in log_content:
                    no_match_pattern.append(name)
    
    print(f"\n7. No exact match found in Sunbiz: {len(no_match_pattern)} (from sample of 50)")
    if no_match_pattern:
        print("   Examples:")
        for name in no_match_pattern[:10]:
            print(f"   - {name}")
    
    # Export failed companies for manual review
    output_file = "failed_lookups.csv"
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Company Name', 'Name Length', 'Has Corporate Suffix', 'Looks Like Personal Name', 'Has Special Chars'])
        
        for name in failed_companies:
            has_suffix = any(suffix in name.upper() for suffix in ['INC', 'LLC', 'CORP', 'COMPANY', 'CO', 'LTD'])
            is_personal = name in personal_names
            has_special = any(char in name for char in ['&', '/', '#', '@', '(', ')', '-'])
            
            writer.writerow([name, len(name), has_suffix, is_personal, has_special])
    
    print(f"\n{'='*60}")
    print(f"Failed lookups exported to: {output_file}")
    
    # Summary of patterns
    print(f"\n{'='*60}")
    print("SUMMARY OF FAILURE PATTERNS:")
    print(f"{'='*60}")
    
    total_explained = len(personal_names) + len(dba_names)
    print(f"Personal names (individuals, not corporations): {len(personal_names)} ({len(personal_names)/len(failed_companies)*100:.1f}%)")
    print(f"DBA names: {len(dba_names)} ({len(dba_names)/len(failed_companies)*100:.1f}%)")
    print(f"Names with special characters: {len(special_char_names)} ({len(special_char_names)/len(failed_companies)*100:.1f}%)")
    print(f"Very long names: {len(long_names)} ({len(long_names)/len(failed_companies)*100:.1f}%)")
    
    print(f"\nPrimary issue: ~{len(personal_names)/len(failed_companies)*100:.0f}% of failures appear to be individual names, not registered businesses")
    
    return failed_companies

if __name__ == "__main__":
    failures = analyze_failures()