#!/usr/bin/env python3
"""
Simple Batch Processor for CSV Enrichment with Resource Management
"""

import subprocess
import time
import psutil
import sys
import os
from pathlib import Path
import pandas as pd
import signal

class SimpleBatchProcessor:
    def __init__(self, input_file, output_file):
        self.input_file = Path(input_file)
        self.output_file = Path(output_file)
        self.temp_dir = self.input_file.parent / "batch_temp"
        self.temp_dir.mkdir(exist_ok=True)
        self.shutdown = False
        
        # Setup signal handler
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        print("\nShutdown requested, finishing current batch...")
        self.shutdown = True
        
    def split_csv(self, batch_size=50):
        """Split input CSV into smaller batches"""
        df = pd.read_csv(self.input_file)
        total_records = len(df)
        batches = []
        
        for i in range(0, total_records, batch_size):
            batch_df = df[i:i+batch_size]
            batch_file = self.temp_dir / f"batch_{i//batch_size:04d}.csv"
            batch_df.to_csv(batch_file, index=False)
            batches.append(batch_file)
            
        print(f"Split {total_records} records into {len(batches)} batches")
        return batches
        
    def wait_for_resources(self, max_memory=60, max_cpu=50):
        """Wait until system resources are available"""
        while not self.shutdown:
            mem = psutil.virtual_memory().percent
            cpu = psutil.cpu_percent(interval=1)
            
            if mem < max_memory and cpu < max_cpu:
                return True
                
            print(f"Waiting for resources (Memory: {mem:.1f}%, CPU: {cpu:.1f}%)...")
            time.sleep(10)
            
        return False
        
    def process_batch(self, batch_file, output_file, concurrency=2):
        """Process a single batch file"""
        cmd = [
            sys.executable, "-m", "auto_enrich.enricher_v2",
            "--input", str(batch_file),
            "--output", str(output_file),
            "--concurrency", str(concurrency)
        ]
        
        print(f"Processing {batch_file.name}...")
        
        try:
            # Run with timeout of 30 minutes per batch
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800,
                check=False
            )
            
            if result.returncode == 0:
                print(f"✓ Successfully processed {batch_file.name}")
                return True
            else:
                print(f"✗ Failed to process {batch_file.name}: {result.stderr[:200]}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"✗ Timeout processing {batch_file.name}")
            return False
        except Exception as e:
            print(f"✗ Error processing {batch_file.name}: {e}")
            return False
            
    def merge_results(self, result_files):
        """Merge all result files into final output"""
        all_dfs = []
        
        for file in result_files:
            if file.exists():
                df = pd.read_csv(file)
                all_dfs.append(df)
                
        if all_dfs:
            merged_df = pd.concat(all_dfs, ignore_index=True)
            merged_df.to_csv(self.output_file, index=False)
            print(f"Merged {len(all_dfs)} batches into {self.output_file}")
            return len(merged_df)
        return 0
        
    def run(self, batch_size=50, concurrency=2, max_memory=60, max_cpu=50):
        """Main processing loop"""
        print(f"Starting batch processing of {self.input_file}")
        print(f"Settings: batch_size={batch_size}, concurrency={concurrency}")
        print(f"Resource limits: max_memory={max_memory}%, max_cpu={max_cpu}%")
        
        # Split into batches
        batches = self.split_csv(batch_size)
        result_files = []
        processed = 0
        failed = 0
        
        # Process each batch
        for i, batch_file in enumerate(batches):
            if self.shutdown:
                print("Shutdown requested, stopping...")
                break
                
            # Wait for resources
            if not self.wait_for_resources(max_memory, max_cpu):
                break
                
            # Process batch
            output_file = self.temp_dir / f"result_{i:04d}.csv"
            success = self.process_batch(batch_file, output_file, concurrency)
            
            if success and output_file.exists():
                result_files.append(output_file)
                processed += 1
            else:
                failed += 1
                
            # Show progress
            progress = (i + 1) / len(batches) * 100
            print(f"Progress: {progress:.1f}% ({i+1}/{len(batches)} batches)")
            print(f"Memory: {psutil.virtual_memory().percent:.1f}%, CPU: {psutil.cpu_percent(interval=0.1):.1f}%")
            print("-" * 50)
            
            # Brief pause between batches
            time.sleep(5)
            
        # Merge results
        total_records = self.merge_results(result_files)
        
        # Summary
        print("\n" + "=" * 50)
        print("BATCH PROCESSING COMPLETE")
        print(f"Processed batches: {processed}/{len(batches)}")
        print(f"Failed batches: {failed}")
        print(f"Total records in output: {total_records}")
        print(f"Output file: {self.output_file}")
        
        # Cleanup
        if processed == len(batches):
            print("Cleaning up temporary files...")
            for file in self.temp_dir.glob("*.csv"):
                file.unlink()
            self.temp_dir.rmdir()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Batch process CSV enrichment")
    parser.add_argument("--input", required=True, help="Input CSV file")
    parser.add_argument("--output", required=True, help="Output CSV file")
    parser.add_argument("--batch-size", type=int, default=50, help="Records per batch")
    parser.add_argument("--concurrency", type=int, default=2, help="Concurrent enrichments")
    parser.add_argument("--max-memory", type=int, default=60, help="Max memory %")
    parser.add_argument("--max-cpu", type=int, default=50, help="Max CPU %")
    
    args = parser.parse_args()
    
    processor = SimpleBatchProcessor(args.input, args.output)
    processor.run(
        batch_size=args.batch_size,
        concurrency=args.concurrency,
        max_memory=args.max_memory,
        max_cpu=args.max_cpu
    )