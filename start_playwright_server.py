#!/usr/bin/env python3
"""
Simple server starter for Windows with Playwright support.
No reload to avoid multiprocessing conflicts.
"""

import os
import sys
import asyncio
from multiprocessing import freeze_support

def main():
    """Main entry point with proper Windows setup."""
    
    # Required for Windows multiprocessing
    if sys.platform == 'win32':
        freeze_support()
        # Set ProactorEventLoop for Playwright subprocess support
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        print("✓ Windows ProactorEventLoop configured for Playwright")
    
    # Set environment to use Playwright
    os.environ['USE_PLAYWRIGHT'] = 'true'
    print("✓ Playwright mode enabled (no browser windows)")
    
    # Initialize database
    print("\nInitializing database...")
    try:
        from app.db.connection import init_db
        init_db()
        print("✓ Database initialized")
    except Exception as e:
        print(f"⚠ Database warning: {e}")
    
    # Import and run uvicorn
    print("\nStarting server on http://localhost:8000")
    print("Frontend at: http://localhost:3000/unified.html")
    print("\nPress CTRL+C to stop\n")
    
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable reload to avoid Windows multiprocessing issues
        log_level="info"
    )

if __name__ == '__main__':
    main()