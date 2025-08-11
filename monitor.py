#!/usr/bin/env python3
"""
Real-time monitor for the AI Sales Agent server.
Shows all API calls, database activity, and processing status.
"""

import time
import os
import sys
from datetime import datetime
import sqlite3
from pathlib import Path

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_job_stats():
    """Get statistics from the database"""
    db_path = Path("data/app.db")
    if not db_path.exists():
        return None
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get job counts by status
        cursor.execute("""
            SELECT status, COUNT(*) 
            FROM jobs 
            GROUP BY status
        """)
        job_stats = dict(cursor.fetchall())
        
        # Get total records processed
        cursor.execute("""
            SELECT COUNT(*) 
            FROM records
        """)
        total_records = cursor.fetchone()[0]
        
        # Get recent jobs
        cursor.execute("""
            SELECT id, status, total_records, processed_records, created_at
            FROM jobs
            ORDER BY created_at DESC
            LIMIT 5
        """)
        recent_jobs = cursor.fetchall()
        
        conn.close()
        
        return {
            'job_stats': job_stats,
            'total_records': total_records,
            'recent_jobs': recent_jobs
        }
    except Exception as e:
        return {'error': str(e)}

def check_directories():
    """Check for files in upload/output directories"""
    uploads = list(Path("uploads").glob("*")) if Path("uploads").exists() else []
    outputs = list(Path("outputs").glob("*")) if Path("outputs").exists() else []
    
    return {
        'uploads': len(uploads),
        'outputs': len(outputs),
        'latest_upload': uploads[-1].name if uploads else None,
        'latest_output': outputs[-1].name if outputs else None
    }

def monitor():
    """Main monitoring loop"""
    print("AI Sales Agent - Live Monitor")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    while True:
        clear_screen()
        
        # Header
        print("+" + "-" * 58 + "+")
        print("|" + " AI SALES AGENT - LIVE MONITOR ".center(58) + "|")
        print("|" + f" {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ".center(58) + "|")
        print("+" + "-" * 58 + "+")
        print()
        
        # Check server status
        import socket
        
        def check_port(port):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            return result == 0
        
        backend_status = "RUNNING" if check_port(8001) else "STOPPED"
        frontend_status = "RUNNING" if check_port(3001) else "STOPPED"
        
        print("SERVER STATUS:")
        print(f"  Backend (API)     : {backend_status} - http://localhost:8001")
        print(f"  Frontend (Web)    : {frontend_status} - http://localhost:3001")
        print()
        
        # Database statistics
        stats = get_job_stats()
        if stats and 'job_stats' in stats:
            print("DATABASE STATISTICS:")
            print(f"  Total Records Processed: {stats['total_records']}")
            print("  Jobs by Status:")
            for status, count in stats['job_stats'].items():
                print(f"    {status.upper()}: {count}")
            print()
            
            if stats['recent_jobs']:
                print("RECENT JOBS:")
                for job in stats['recent_jobs'][:3]:
                    job_id = job[0][:8] + "..."
                    status = job[1]
                    total = job[2]
                    processed = job[3]
                    created = job[4]
                    print(f"  {job_id} | {status:10} | {processed}/{total} records | {created}")
            print()
        
        # File system check
        dir_stats = check_directories()
        print("FILE SYSTEM:")
        print(f"  Upload Files  : {dir_stats['uploads']}")
        print(f"  Output Files  : {dir_stats['outputs']}")
        if dir_stats['latest_upload']:
            print(f"  Latest Upload : {dir_stats['latest_upload']}")
        if dir_stats['latest_output']:
            print(f"  Latest Output : {dir_stats['latest_output']}")
        print()
        
        # Check for log file
        log_file = Path("logs/app.log")
        if log_file.exists():
            # Get last 5 lines of log
            with open(log_file, 'r') as f:
                lines = f.readlines()
                recent_logs = lines[-5:] if len(lines) > 5 else lines
            
            print("RECENT LOGS:")
            for line in recent_logs:
                print(f"  {line.strip()[:70]}...")
        
        print()
        print("=" * 60)
        print("URLs:")
        print("  Web Interface : http://localhost:3001/test.html")
        print("  API Docs      : http://localhost:8001/docs")
        print()
        print("Press Ctrl+C to stop monitoring")
        
        time.sleep(2)  # Refresh every 2 seconds

if __name__ == "__main__":
    try:
        monitor()
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")
        sys.exit(0)