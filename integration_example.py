"""
Integration example showing how to use the enhanced LLM service
with the existing job processing system.

This demonstrates how to integrate the new content generation system
into the existing workflow while maintaining backward compatibility.
"""

import asyncio
import pandas as pd
import json
from datetime import datetime
from typing import List, Dict, Any

# Import existing system components
import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.join(current_dir, 'app'))

from app.services.content_generator import content_generator, ContentRequest
from app.prompts.templates import DealershipType, EmailTone
from auto_enrich.ai_enrichment import generate_enhanced_email_content


class EnhancedDealershipProcessor:
    """Enhanced processor that uses the new LLM service for dealership data enrichment."""
    
    def __init__(self):
        self.generation_stats = {
            'total_processed': 0,
            'total_cost': 0.0,
            'total_tokens': 0,
            'cache_hits': 0,
            'quality_scores': [],
            'processing_times': [],
            'errors': []
        }
    
    def determine_dealership_type(self, dealer_name: str, website: str = None, context: str = None) -> DealershipType:
        """Determine dealership type from available information."""
        name_lower = dealer_name.lower()
        context_lower = (context or "").lower()
        website_lower = (website or "").lower()
        
        # Check for luxury brands
        luxury_indicators = [
            'mercedes', 'bmw', 'audi', 'lexus', 'porsche', 'jaguar', 'land rover',
            'bentley', 'maserati', 'ferrari', 'lamborghini', 'tesla', 'luxury',
            'premium', 'elite', 'prestige'
        ]
        
        # Check for new car dealer indicators
        new_car_indicators = [
            'ford', 'chevrolet', 'toyota', 'honda', 'nissan', 'hyundai',
            'volkswagen', 'subaru', 'mazda', 'kia', 'chrysler', 'dodge',
            'jeep', 'ram', 'gmc', 'buick', 'cadillac'
        ]
        
        # Check for motorcycle indicators
        motorcycle_indicators = [
            'motorcycle', 'harley', 'yamaha', 'kawasaki', 'suzuki',
            'ducati', 'triumph', 'bike', 'cycle'
        ]
        
        # Check for commercial/truck indicators
        commercial_indicators = [
            'truck', 'commercial', 'fleet', 'cargo', 'freight',
            'work truck', 'utility', 'van'
        ]
        
        all_text = f"{name_lower} {context_lower} {website_lower}"
        
        if any(indicator in all_text for indicator in luxury_indicators):
            return DealershipType.LUXURY
        elif any(indicator in all_text for indicator in new_car_indicators):
            return DealershipType.NEW_CAR
        elif any(indicator in all_text for indicator in motorcycle_indicators):
            return DealershipType.MOTORCYCLE
        elif any(indicator in all_text for indicator in commercial_indicators):
            return DealershipType.COMMERCIAL
        else:
            return DealershipType.USED_CAR
    
    def select_optimal_tones(self, dealership_type: DealershipType, context: str = None) -> List[EmailTone]:
        """Select optimal email tones based on dealership type and context."""
        if dealership_type == DealershipType.LUXURY:
            return [EmailTone.PROFESSIONAL, EmailTone.URGENT]
        elif dealership_type == DealershipType.NEW_CAR:
            return [EmailTone.PROFESSIONAL, EmailTone.FRIENDLY]
        elif dealership_type == DealershipType.USED_CAR:
            return [EmailTone.FRIENDLY, EmailTone.URGENT]
        else:
            return [EmailTone.PROFESSIONAL, EmailTone.FRIENDLY]
    
    async def process_single_dealership(
        self,
        dealer_name: str,
        city: str,
        website: str = None,
        owner_email: str = None,
        context: str = None,
        use_enhanced: bool = True
    ) -> Dict[str, Any]:
        """Process a single dealership with enhanced content generation."""
        start_time = datetime.now()
        
        try:
            if use_enhanced:
                # Use the new enhanced system
                dealership_type = self.determine_dealership_type(dealer_name, website, context)
                optimal_tones = self.select_optimal_tones(dealership_type, context)
                
                request = ContentRequest(
                    dealership_name=dealer_name,
                    city=city,
                    website=website,
                    owner_email=owner_email,
                    dealership_type=dealership_type,
                    extra_context=context,
                    tones=optimal_tones,
                    max_cost_per_record=0.02,
                    quality_threshold=70.0
                )
                
                generated_content = await content_generator.generate_content(request)
                quality_summary = content_generator.get_quality_summary(generated_content)
                
                # Update statistics
                self.generation_stats['total_processed'] += 1
                self.generation_stats['total_cost'] += generated_content.total_cost
                self.generation_stats['total_tokens'] += generated_content.total_tokens
                self.generation_stats['quality_scores'].append(quality_summary['overall_quality'])
                
                # Count cache hits
                cache_hits = sum(1 for v in generated_content.variations if v.cached)
                self.generation_stats['cache_hits'] += cache_hits
                
                processing_time = (datetime.now() - start_time).total_seconds()
                self.generation_stats['processing_times'].append(processing_time)
                
                # Format results
                result = {
                    'dealership_name': dealer_name,
                    'city': city,
                    'owner_name': generated_content.owner_name,
                    'dealership_type': dealership_type.value,
                    'processing_time': processing_time,
                    'cost': generated_content.total_cost,
                    'tokens': generated_content.total_tokens,
                    'quality_score': quality_summary['overall_quality'],
                    'variations': []
                }
                
                for variation in generated_content.variations:
                    result['variations'].append({
                        'tone': variation.tone.value,
                        'subject': variation.subject,
                        'icebreaker': variation.icebreaker,
                        'hot_button': variation.hot_button,
                        'quality_scores': variation.quality_scores,
                        'cached': variation.cached
                    })
                
                return result
            
            else:
                # Use backward-compatible method
                from auto_enrich.ai_enrichment import generate_email_content
                
                subject, icebreaker, hot_button = await generate_email_content(
                    dealer_name, city, website, owner_email, context
                )
                
                processing_time = (datetime.now() - start_time).total_seconds()
                
                return {
                    'dealership_name': dealer_name,
                    'city': city,
                    'processing_time': processing_time,
                    'cost': 0.01,  # Estimated
                    'variations': [{
                        'tone': 'professional',
                        'subject': subject,
                        'icebreaker': icebreaker,
                        'hot_button': hot_button,
                        'quality_scores': {'overall_score': 75.0},
                        'cached': False
                    }]
                }
        
        except Exception as e:
            self.generation_stats['errors'].append({
                'dealership': dealer_name,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            
            # Return fallback result
            return {
                'dealership_name': dealer_name,
                'city': city,
                'error': str(e),
                'cost': 0.0,
                'variations': []
            }
    
    async def process_csv_file(
        self,
        csv_file_path: str,
        output_file_path: str = None,
        max_concurrent: int = 3,
        use_enhanced: bool = True
    ) -> Dict[str, Any]:
        """Process a CSV file of dealership data."""
        print(f"Processing CSV file: {csv_file_path}")
        print(f"Enhanced mode: {use_enhanced}")
        
        # Read CSV
        try:
            df = pd.read_csv(csv_file_path)
            print(f"Loaded {len(df)} records")
        except Exception as e:
            return {'error': f"Failed to read CSV: {e}"}
        
        # Expected columns (flexible mapping)
        column_mapping = {
            'dealership_name': ['dealership_name', 'dealer_name', 'business_name', 'name'],
            'city': ['city', 'location'],
            'website': ['website', 'url', 'web_address'],
            'owner_email': ['owner_email', 'email', 'contact_email'],
            'context': ['context', 'description', 'notes', 'extra_context']
        }
        
        # Map columns
        mapped_columns = {}
        for target, possible_names in column_mapping.items():
            for col_name in possible_names:
                if col_name in df.columns:
                    mapped_columns[target] = col_name
                    break
        
        print(f"Column mapping: {mapped_columns}")
        
        # Prepare processing tasks
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_row_with_limit(row):
            async with semaphore:
                return await self.process_single_dealership(
                    dealer_name=row.get(mapped_columns.get('dealership_name', 'dealership_name'), ''),
                    city=row.get(mapped_columns.get('city', 'city'), ''),
                    website=row.get(mapped_columns.get('website', 'website'), None),
                    owner_email=row.get(mapped_columns.get('owner_email', 'owner_email'), None),
                    context=row.get(mapped_columns.get('context', 'context'), None),
                    use_enhanced=use_enhanced
                )
        
        # Process all rows
        start_time = datetime.now()
        tasks = [process_row_with_limit(row) for _, row in df.iterrows()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = datetime.now()
        
        # Filter successful results
        successful_results = [r for r in results if not isinstance(r, Exception)]
        
        # Generate summary
        total_time = (end_time - start_time).total_seconds()
        summary = {
            'total_records': len(df),
            'successful_records': len(successful_results),
            'failed_records': len(results) - len(successful_results),
            'total_processing_time': total_time,
            'average_time_per_record': total_time / len(df) if len(df) > 0 else 0,
            'total_cost': self.generation_stats['total_cost'],
            'average_cost_per_record': self.generation_stats['total_cost'] / len(successful_results) if successful_results else 0,
            'total_tokens': self.generation_stats['total_tokens'],
            'cache_hit_rate': (self.generation_stats['cache_hits'] / max(1, self.generation_stats['total_processed'])) * 100,
            'average_quality_score': sum(self.generation_stats['quality_scores']) / len(self.generation_stats['quality_scores']) if self.generation_stats['quality_scores'] else 0,
            'errors': self.generation_stats['errors']
        }
        
        # Save results
        if output_file_path:
            output_data = {
                'summary': summary,
                'results': successful_results,
                'timestamp': datetime.now().isoformat()
            }
            
            with open(output_file_path, 'w') as f:
                json.dump(output_data, f, indent=2)
            
            print(f"Results saved to: {output_file_path}")
        
        return {
            'summary': summary,
            'results': successful_results
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return dict(self.generation_stats)


async def demonstrate_integration():
    """Demonstrate the integration with sample data."""
    print("🚀 Demonstrating Enhanced Dealership Processing Integration")
    print("=" * 60)
    
    # Create sample data
    sample_data = [
        {
            'dealership_name': 'Luxury Motors Miami',
            'city': 'Miami',
            'website': 'https://luxurymotorsmiami.com',
            'owner_email': 'john.smith@luxurymotorsmiami.com',
            'context': 'Specializes in BMW, Mercedes, and Audi. Family-owned for 20 years.'
        },
        {
            'dealership_name': 'Budget Auto Sales',
            'city': 'Orlando',
            'website': None,
            'owner_email': 'mike@budgetauto.net',
            'context': 'Affordable used cars, financing available, community-focused'
        },
        {
            'dealership_name': 'Downtown Honda',
            'city': 'Tampa',
            'website': 'https://downtownhonda.com',
            'owner_email': 'info@downtownhonda.com',
            'context': 'New Honda dealership with full service department'
        }
    ]
    
    # Create sample CSV
    df = pd.DataFrame(sample_data)
    csv_path = 'sample_dealerships.csv'
    df.to_csv(csv_path, index=False)
    
    # Process with enhanced system
    processor = EnhancedDealershipProcessor()
    
    print("Processing sample dealerships with enhanced system...")
    results = await processor.process_csv_file(
        csv_path, 
        'enhanced_results.json',
        max_concurrent=2,
        use_enhanced=True
    )
    
    # Display summary
    summary = results['summary']
    print(f"\n📊 Processing Summary:")
    print(f"  Total records: {summary['total_records']}")
    print(f"  Successful: {summary['successful_records']}")
    print(f"  Failed: {summary['failed_records']}")
    print(f"  Total cost: ${summary['total_cost']:.4f}")
    print(f"  Avg cost per record: ${summary['average_cost_per_record']:.4f}")
    print(f"  Avg quality score: {summary['average_quality_score']:.1f}/100")
    print(f"  Cache hit rate: {summary['cache_hit_rate']:.1f}%")
    print(f"  Total processing time: {summary['total_processing_time']:.2f} seconds")
    
    # Show sample results
    if results['results']:
        print(f"\n📝 Sample Generated Content:")
        for i, result in enumerate(results['results'][:2]):  # Show first 2
            print(f"\n--- {result['dealership_name']} ---")
            print(f"Type: {result.get('dealership_type', 'N/A')}")
            print(f"Quality: {result.get('quality_score', 0):.1f}/100")
            
            if result.get('variations'):
                for variation in result['variations']:
                    print(f"\n{variation['tone'].title()} Tone:")
                    print(f"  Subject: {variation['subject']}")
                    print(f"  Icebreaker: {variation['icebreaker'][:100]}...")
    
    # Compare with backward compatible mode
    print(f"\n🔄 Comparing with backward compatible mode...")
    processor_legacy = EnhancedDealershipProcessor()
    
    legacy_results = await processor_legacy.process_csv_file(
        csv_path,
        'legacy_results.json', 
        max_concurrent=2,
        use_enhanced=False
    )
    
    legacy_summary = legacy_results['summary']
    print(f"Legacy mode - Avg time per record: {legacy_summary['average_time_per_record']:.2f}s")
    print(f"Enhanced mode - Avg time per record: {summary['average_time_per_record']:.2f}s")
    
    # Cleanup
    import os
    os.remove(csv_path)
    
    print(f"\n✅ Integration demonstration completed!")
    print(f"📄 Enhanced results saved to: enhanced_results.json")
    print(f"📄 Legacy results saved to: legacy_results.json")


async def cost_analysis_example():
    """Demonstrate cost analysis and optimization."""
    print(f"\n💰 Cost Analysis and Optimization")
    print("=" * 40)
    
    processor = EnhancedDealershipProcessor()
    
    # Test different scenarios
    scenarios = [
        {
            'name': 'Single tone (cost-optimized)',
            'tones': [EmailTone.PROFESSIONAL],
            'max_cost': 0.01
        },
        {
            'name': 'Dual tone (balanced)',
            'tones': [EmailTone.PROFESSIONAL, EmailTone.FRIENDLY],
            'max_cost': 0.015
        },
        {
            'name': 'Triple tone (premium)',
            'tones': [EmailTone.PROFESSIONAL, EmailTone.FRIENDLY, EmailTone.URGENT],
            'max_cost': 0.02
        }
    ]
    
    for scenario in scenarios:
        request = ContentRequest(
            dealership_name="Test Motors",
            city="Test City",
            owner_email="test@testmotors.com",
            tones=scenario['tones'],
            max_cost_per_record=scenario['max_cost']
        )
        
        result = await content_generator.generate_content(request)
        
        print(f"\n{scenario['name']}:")
        print(f"  Budget: ${scenario['max_cost']:.3f}")
        print(f"  Actual cost: ${result.total_cost:.4f}")
        print(f"  Variations: {len(result.variations)}")
        print(f"  Tokens: {result.total_tokens}")
        print(f"  Time: {result.generation_time:.2f}s")


if __name__ == "__main__":
    asyncio.run(demonstrate_integration())
    asyncio.run(cost_analysis_example())