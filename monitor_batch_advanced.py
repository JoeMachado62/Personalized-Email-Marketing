#!/usr/bin/env python3
"""
Advanced Batch Processing Monitor with Real-time Statistics
"""

import os
import sys
import time
import psutil
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
from collections import deque

class BatchMonitor:
    def __init__(self):
        self.batch_dir = Path("uploads/batch_temp")
        self.log_file = Path("batch_processing.log")
        self.history = deque(maxlen=10)  # Keep last 10 measurements
        
    def get_process_info(self):
        """Find and get info about batch processor"""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
            try:
                if 'simple_batch_processor' in ' '.join(proc.info['cmdline'] or []):
                    return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None
    
    def get_batch_stats(self):
        """Get batch processing statistics"""
        if not self.batch_dir.exists():
            return None
            
        batch_files = list(self.batch_dir.glob("batch_*.csv"))
        result_files = list(self.batch_dir.glob("result_*.csv"))
        
        # Get current processing batch from log
        current_batch = None
        if self.log_file.exists():
            try:
                recent_lines = subprocess.run(
                    ["tail", "-20", str(self.log_file)],
                    capture_output=True, text=True
                ).stdout
                
                for line in recent_lines.split('\n'):
                    if "Processing batch_" in line:
                        import re
                        match = re.search(r'batch_(\d+)', line)
                        if match:
                            current_batch = int(match.group(1))
            except:
                pass
        
        return {
            'total_batches': len(batch_files),
            'completed_batches': len(result_files),
            'current_batch': current_batch,
            'progress_percent': (len(result_files) / len(batch_files) * 100) if batch_files else 0
        }
    
    def get_enrichment_subprocess(self):
        """Check if enricher_v2 subprocess is running"""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'enricher_v2' in cmdline and '--input' in cmdline:
                    return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None
    
    def estimate_completion(self, stats):
        """Estimate completion time based on progress"""
        if not stats or stats['completed_batches'] == 0:
            return None
            
        # Read first result file to get timing
        result_files = sorted(self.batch_dir.glob("result_*.csv"))
        if not result_files:
            return None
            
        # Get process start time
        proc = self.get_process_info()
        if not proc:
            return None
            
        try:
            start_time = datetime.fromtimestamp(proc.create_time())
            elapsed = datetime.now() - start_time
            
            # Calculate rate
            batches_per_hour = stats['completed_batches'] / (elapsed.total_seconds() / 3600)
            if batches_per_hour > 0:
                remaining_batches = stats['total_batches'] - stats['completed_batches']
                hours_remaining = remaining_batches / batches_per_hour
                completion_time = datetime.now() + timedelta(hours=hours_remaining)
                return {
                    'elapsed': elapsed,
                    'rate': batches_per_hour,
                    'eta': completion_time,
                    'hours_remaining': hours_remaining
                }
        except:
            return None
    
    def check_for_errors(self):
        """Check for recent errors in log"""
        if not self.log_file.exists():
            return []
            
        errors = []
        try:
            recent_lines = subprocess.run(
                ["tail", "-100", str(self.log_file)],
                capture_output=True, text=True
            ).stdout
            
            for line in recent_lines.split('\n'):
                if any(word in line.lower() for word in ['error', 'failed', 'exception', 'timeout']):
                    errors.append(line.strip())
        except:
            pass
            
        return errors[-5:]  # Return last 5 errors
    
    def get_resource_usage(self):
        """Get current resource usage"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Check if we're waiting for resources
        waiting = False
        if self.log_file.exists():
            try:
                last_line = subprocess.run(
                    ["tail", "-1", str(self.log_file)],
                    capture_output=True, text=True
                ).stdout.strip()
                waiting = "Waiting for resources" in last_line
            except:
                pass
        
        return {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_used_gb': memory.used / (1024**3),
            'memory_total_gb': memory.total / (1024**3),
            'disk_percent': disk.percent,
            'waiting': waiting
        }
    
    def get_output_stats(self):
        """Check output file statistics"""
        output_files = list(Path('.').glob("a7e98f55*.csv"))
        stats = {}
        
        for file in output_files:
            if file.exists():
                try:
                    df = pd.read_csv(file, nrows=5)  # Just read header
                    num_rows = sum(1 for _ in open(file)) - 1  # Count rows
                    stats[file.name] = {
                        'rows': num_rows,
                        'size_mb': file.stat().st_size / (1024**2),
                        'modified': datetime.fromtimestamp(file.stat().st_mtime)
                    }
                except:
                    pass
                    
        return stats
    
    def display_monitor(self):
        """Display comprehensive monitoring information"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("=" * 80)
        print("BATCH PROCESSING MONITOR".center(80))
        print("=" * 80)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Process Status
        proc = self.get_process_info()
        if proc:
            try:
                print("✅ BATCH PROCESSOR: RUNNING")
                print(f"   PID: {proc.pid}")
                print(f"   CPU: {proc.cpu_percent(interval=0.1):.1f}%")
                print(f"   Memory: {proc.memory_info().rss / (1024**2):.1f} MB")
            except:
                print("✅ BATCH PROCESSOR: RUNNING")
        else:
            print("❌ BATCH PROCESSOR: NOT RUNNING")
        
        # Check enrichment subprocess
        enrich_proc = self.get_enrichment_subprocess()
        if enrich_proc:
            print(f"   └─ Enricher subprocess active (PID: {enrich_proc.pid})")
        
        print()
        
        # Batch Statistics
        stats = self.get_batch_stats()
        if stats:
            print(f"📊 BATCH PROGRESS:")
            print(f"   Completed: {stats['completed_batches']}/{stats['total_batches']} batches")
            print(f"   Progress: [{'█' * int(stats['progress_percent']/5)}{'-' * (20-int(stats['progress_percent']/5))}] {stats['progress_percent']:.1f}%")
            
            if stats['current_batch'] is not None:
                print(f"   Currently processing: batch_{stats['current_batch']:04d}.csv")
            
            # Time estimates
            estimate = self.estimate_completion(stats)
            if estimate:
                print(f"\n⏱️  TIME ESTIMATES:")
                print(f"   Elapsed: {str(estimate['elapsed']).split('.')[0]}")
                print(f"   Rate: {estimate['rate']:.2f} batches/hour")
                print(f"   ETA: {estimate['eta'].strftime('%Y-%m-%d %H:%M')}")
                print(f"   Remaining: {estimate['hours_remaining']:.1f} hours")
        
        print()
        
        # Resource Usage
        resources = self.get_resource_usage()
        print(f"💻 SYSTEM RESOURCES:")
        print(f"   CPU: {resources['cpu_percent']:.1f}% {'⚠️ WAITING' if resources['waiting'] else '✓'}")
        print(f"   Memory: {resources['memory_used_gb']:.1f}/{resources['memory_total_gb']:.1f} GB ({resources['memory_percent']:.1f}%)")
        print(f"   Disk: {resources['disk_percent']:.1f}% used")
        
        # Output Files
        output_stats = self.get_output_stats()
        if output_stats:
            print(f"\n📁 OUTPUT FILES:")
            for filename, info in output_stats.items():
                print(f"   {filename}: {info['rows']} rows, {info['size_mb']:.1f} MB")
                print(f"      Last modified: {info['modified'].strftime('%H:%M:%S')}")
        
        # Recent Errors
        errors = self.check_for_errors()
        if errors:
            print(f"\n⚠️  RECENT ISSUES:")
            for error in errors[-3:]:  # Show last 3
                print(f"   • {error[:100]}...")
        
        print()
        print("-" * 80)
        print("Commands: [q]uit | [l]ogs | [r]efresh | [k]ill process")
        
    def show_logs(self):
        """Display recent log entries"""
        if self.log_file.exists():
            subprocess.run(["tail", "-30", str(self.log_file)])
    
    def kill_process(self):
        """Kill the batch processor"""
        proc = self.get_process_info()
        if proc:
            proc.terminate()
            print("Batch processor terminated.")
        else:
            print("No batch processor found.")
    
    def run_interactive(self):
        """Run interactive monitor"""
        try:
            while True:
                self.display_monitor()
                
                # Wait for input with timeout
                import select
                timeout = 5  # Refresh every 5 seconds
                
                if sys.stdin in select.select([sys.stdin], [], [], timeout)[0]:
                    cmd = sys.stdin.readline().strip().lower()
                    
                    if cmd == 'q':
                        break
                    elif cmd == 'l':
                        self.show_logs()
                        input("\nPress Enter to continue...")
                    elif cmd == 'k':
                        if input("Kill batch processor? (y/n): ").lower() == 'y':
                            self.kill_process()
                            time.sleep(2)
                    elif cmd == 'r':
                        continue  # Refresh immediately
                        
        except KeyboardInterrupt:
            print("\nMonitor stopped.")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor batch processing")
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--json', action='store_true', help='Output JSON format')
    
    args = parser.parse_args()
    
    monitor = BatchMonitor()
    
    if args.once:
        # Single run mode
        stats = monitor.get_batch_stats()
        resources = monitor.get_resource_usage()
        proc = monitor.get_process_info()
        
        if args.json:
            import json
            output = {
                'running': proc is not None,
                'batch_stats': stats,
                'resources': resources,
                'timestamp': datetime.now().isoformat()
            }
            print(json.dumps(output, indent=2, default=str))
        else:
            monitor.display_monitor()
    else:
        # Interactive mode
        monitor.run_interactive()

if __name__ == '__main__':
    main()