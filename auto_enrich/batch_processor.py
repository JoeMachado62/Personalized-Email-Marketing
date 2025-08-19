#!/usr/bin/env python3
"""
Robust Batch Processor for CSV Enrichment
Resource-aware processing with automatic resume capability
"""

import asyncio
import pandas as pd
import psutil
import os
import sys
import json
import time
import signal
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass, field, asdict
import argparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from auto_enrich.enricher_v2 import EnrichmentResult

async def enrich_single_record(record_dict):
    """Wrapper to enrich a single record"""
    from auto_enrich.enricher_v2 import enrich_record_async
    import pandas as pd
    
    # Convert dict to Series for processing
    record = pd.Series(record_dict)
    result = await enrich_record_async(record)
    return result

@dataclass
class BatchConfig:
    """Configuration for batch processing"""
    max_memory_percent: float = 60.0  # Max memory usage percentage
    max_cpu_percent: float = 70.0     # Target CPU usage
    batch_size: int = 50               # Records per batch
    concurrency: int = 3               # Concurrent enrichments
    checkpoint_interval: int = 25      # Save progress every N records
    timeout_per_record: int = 120      # Seconds per record timeout
    retry_attempts: int = 2            # Retry failed records
    
@dataclass
class BatchState:
    """Persistent state for batch processing"""
    input_file: str
    output_file: str
    total_records: int
    processed_records: int = 0
    failed_records: List[int] = field(default_factory=list)
    completed_batches: List[int] = field(default_factory=list)
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    last_checkpoint: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def save(self, filepath: Path):
        """Save state to JSON file"""
        with open(filepath, 'w') as f:
            json.dump(asdict(self), f, indent=2)
    
    @classmethod
    def load(cls, filepath: Path) -> 'BatchState':
        """Load state from JSON file"""
        with open(filepath, 'r') as f:
            return cls(**json.load(f))

class ResourceMonitor:
    """Monitor system resources and throttle processing"""
    
    def __init__(self, config: BatchConfig):
        self.config = config
        self.process = psutil.Process()
        
    def check_resources(self) -> Tuple[bool, str]:
        """Check if resources are available for processing"""
        # Check memory
        memory_percent = psutil.virtual_memory().percent
        if memory_percent > self.config.max_memory_percent:
            return False, f"Memory usage too high: {memory_percent:.1f}%"
        
        # Check CPU (average over 1 second)
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > self.config.max_cpu_percent:
            return False, f"CPU usage too high: {cpu_percent:.1f}%"
        
        return True, "Resources OK"
    
    def get_optimal_concurrency(self) -> int:
        """Dynamically adjust concurrency based on resources"""
        memory_percent = psutil.virtual_memory().percent
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # Reduce concurrency if resources are constrained
        if memory_percent > 50 or cpu_percent > 60:
            return max(1, self.config.concurrency - 1)
        elif memory_percent < 30 and cpu_percent < 40:
            return min(5, self.config.concurrency + 1)
        return self.config.concurrency

class BatchProcessor:
    """Main batch processor with resource management"""
    
    def __init__(self, config: BatchConfig):
        self.config = config
        self.monitor = ResourceMonitor(config)
        self.logger = self._setup_logger()
        self.shutdown = False
        self.semaphore = None
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger('BatchProcessor')
        logger.setLevel(logging.INFO)
        
        # Console handler
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console.setFormatter(formatter)
        logger.addHandler(console)
        
        # File handler
        file_handler = logging.FileHandler('batch_processor.log')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        return logger
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info("Shutdown signal received, saving state...")
        self.shutdown = True
    
    async def process_batch(self, df: pd.DataFrame, indices: List[int], 
                           state: BatchState) -> List[EnrichmentResult]:
        """Process a batch of records with concurrency control"""
        results = []
        
        # Dynamic concurrency adjustment
        concurrency = self.monitor.get_optimal_concurrency()
        self.semaphore = asyncio.Semaphore(concurrency)
        
        tasks = []
        for idx in indices:
            if self.shutdown:
                break
            
            row = df.iloc[idx]
            task = self._process_record_with_limit(row, idx)
            tasks.append(task)
        
        # Process with timeout
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for idx, result in zip(indices, batch_results):
            if isinstance(result, Exception):
                self.logger.error(f"Record {idx} failed: {result}")
                state.failed_records.append(idx)
                results.append(None)
            else:
                results.append(result)
        
        return results
    
    async def _process_record_with_limit(self, row: pd.Series, idx: int):
        """Process single record with semaphore and timeout"""
        async with self.semaphore:
            # Wait for resources if needed
            while not self.shutdown:
                can_proceed, message = self.monitor.check_resources()
                if can_proceed:
                    break
                self.logger.info(f"Waiting for resources: {message}")
                await asyncio.sleep(5)
            
            if self.shutdown:
                return None
            
            # Process with timeout
            try:
                result = await asyncio.wait_for(
                    enrich_single_record(row.to_dict()),
                    timeout=self.config.timeout_per_record
                )
                self.logger.info(f"✓ Record {idx}: {row.get('DEALER NAME', 'Unknown')}")
                return result
            except asyncio.TimeoutError:
                self.logger.error(f"✗ Record {idx} timeout")
                raise
            except Exception as e:
                self.logger.error(f"✗ Record {idx} error: {e}")
                raise
    
    def save_checkpoint(self, df: pd.DataFrame, results: List[EnrichmentResult], 
                       state: BatchState, state_file: Path):
        """Save current progress to file"""
        # Convert results to dataframe
        enriched_data = []
        for i, result in enumerate(results):
            if result is None:
                continue
            
            row_data = df.iloc[i].to_dict()
            row_data.update(result.to_dict())
            enriched_data.append(row_data)
        
        if enriched_data:
            enriched_df = pd.DataFrame(enriched_data)
            
            # Save or append to output file
            output_path = Path(state.output_file)
            if output_path.exists():
                existing_df = pd.read_csv(output_path)
                combined_df = pd.concat([existing_df, enriched_df], ignore_index=True)
                combined_df.to_csv(output_path, index=False)
            else:
                enriched_df.to_csv(output_path, index=False)
            
            self.logger.info(f"Checkpoint saved: {len(enriched_data)} records")
        
        # Save state
        state.last_checkpoint = datetime.now().isoformat()
        state.save(state_file)
    
    async def run(self, input_file: str, output_file: str, resume: bool = False):
        """Main processing loop"""
        # Setup paths
        input_path = Path(input_file)
        output_path = Path(output_file)
        state_file = input_path.parent / f".{input_path.stem}_state.json"
        
        # Load or create state
        if resume and state_file.exists():
            state = BatchState.load(state_file)
            self.logger.info(f"Resuming from record {state.processed_records}")
        else:
            df = pd.read_csv(input_path)
            state = BatchState(
                input_file=str(input_path),
                output_file=str(output_path),
                total_records=len(df)
            )
        
        # Load dataframe
        df = pd.read_csv(input_path)
        
        # Process in batches
        batch_num = 0
        all_results = []
        
        while state.processed_records < state.total_records and not self.shutdown:
            # Calculate batch range
            start_idx = state.processed_records
            end_idx = min(start_idx + self.config.batch_size, state.total_records)
            indices = list(range(start_idx, end_idx))
            
            self.logger.info(f"\n--- Batch {batch_num + 1} ---")
            self.logger.info(f"Processing records {start_idx}-{end_idx} of {state.total_records}")
            self.logger.info(f"Memory: {psutil.virtual_memory().percent:.1f}%, "
                           f"CPU: {psutil.cpu_percent(interval=0.1):.1f}%")
            
            # Process batch
            batch_results = await self.process_batch(df, indices, state)
            all_results.extend(batch_results)
            
            # Update state
            state.processed_records = end_idx
            state.completed_batches.append(batch_num)
            
            # Save checkpoint
            if len(all_results) >= self.config.checkpoint_interval:
                self.save_checkpoint(df[:end_idx], all_results, state, state_file)
                all_results = []  # Clear to save memory
            
            batch_num += 1
            
            # Brief pause between batches
            await asyncio.sleep(2)
        
        # Final save
        if all_results:
            self.save_checkpoint(df[:state.processed_records], all_results, state, state_file)
        
        # Summary
        elapsed = datetime.now() - datetime.fromisoformat(state.start_time)
        self.logger.info(f"\n=== Processing Complete ===")
        self.logger.info(f"Total processed: {state.processed_records}/{state.total_records}")
        self.logger.info(f"Failed records: {len(state.failed_records)}")
        self.logger.info(f"Time elapsed: {elapsed}")
        self.logger.info(f"Output saved to: {output_path}")
        
        # Clean up state file if completed
        if state.processed_records >= state.total_records:
            state_file.unlink(missing_ok=True)

def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description='Batch process CSV enrichment')
    parser.add_argument('--input', required=True, help='Input CSV file')
    parser.add_argument('--output', required=True, help='Output CSV file')
    parser.add_argument('--batch-size', type=int, default=50, help='Records per batch')
    parser.add_argument('--concurrency', type=int, default=3, help='Concurrent enrichments')
    parser.add_argument('--max-memory', type=float, default=60.0, help='Max memory usage %')
    parser.add_argument('--max-cpu', type=float, default=70.0, help='Max CPU usage %')
    parser.add_argument('--resume', action='store_true', help='Resume from last checkpoint')
    
    args = parser.parse_args()
    
    # Create configuration
    config = BatchConfig(
        batch_size=args.batch_size,
        concurrency=args.concurrency,
        max_memory_percent=args.max_memory,
        max_cpu_percent=args.max_cpu
    )
    
    # Run processor
    processor = BatchProcessor(config)
    asyncio.run(processor.run(args.input, args.output, args.resume))

if __name__ == '__main__':
    main()