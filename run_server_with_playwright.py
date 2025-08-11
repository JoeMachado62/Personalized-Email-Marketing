#!/usr/bin/env python3
"""
Windows-compatible server startup script with Playwright support.
Sets the ProactorEventLoop BEFORE uvicorn starts to ensure compatibility.
"""

import os
import sys
import subprocess
import time
import webbrowser
from pathlib import Path
import asyncio

# CRITICAL: Set Windows event loop policy BEFORE ANY imports that might create loops
if sys.platform == 'win32':
    # Force ProactorEventLoop for Windows subprocess support (required by Playwright)
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    print("✓ Windows ProactorEventLoop policy set for Playwright compatibility")

def check_port(port):
    """Check if a port is available"""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', port))
    sock.close()
    return result != 0  # True if port is available

def start_backend():
    """Start the FastAPI backend server with proper Windows event loop"""
    print("Starting FastAPI backend server on port 8000...")
    
    # Check if port 8000 is available
    if not check_port(8000):
        print("WARNING: Port 8000 is already in use!")
        print("   Try: netstat -ano | findstr :8000")
        return None
    
    # Set environment variable to ensure Playwright is used
    env = os.environ.copy()
    env['USE_PLAYWRIGHT'] = 'true'
    
    # Create a Python script that sets event loop policy before importing uvicorn
    launcher_script = """
import sys
import asyncio
from multiprocessing import freeze_support

if __name__ == '__main__':
    # Required for Windows multiprocessing
    freeze_support()
    
    # Set Windows event loop policy FIRST
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # Now import and run uvicorn
    import uvicorn
    # NOTE: reload=False to avoid multiprocessing issues on Windows with ProactorEventLoop
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
"""
    
    # Write the launcher script
    launcher_path = Path("_uvicorn_launcher.py")
    launcher_path.write_text(launcher_script)
    
    # Start uvicorn using the launcher script
    cmd = [sys.executable, str(launcher_path)]
    process = subprocess.Popen(cmd, env=env)
    
    # Wait for server to start
    print("   Waiting for server to start...")
    time.sleep(3)
    
    return process

def start_frontend():
    """Start a simple HTTP server for the frontend"""
    print("Starting frontend server on port 3000...")
    
    # Check if port 3000 is available
    if not check_port(3000):
        print("WARNING: Port 3000 is already in use!")
        print("   Try: netstat -ano | findstr :3000")
        return None
    
    # Change to frontend directory
    frontend_path = Path("frontend")
    if not frontend_path.exists():
        print("ERROR: Frontend directory not found!")
        return None
    
    # Start Python HTTP server
    cmd = [sys.executable, "-m", "http.server", "3000", "--directory", "frontend"]
    process = subprocess.Popen(cmd)
    
    print("   Frontend server started!")
    return process

def main():
    print("=" * 60)
    print("AI Sales Agent MVP - Starting Application (Playwright Mode)")
    print("=" * 60)
    
    # Set environment to use Playwright
    os.environ['USE_PLAYWRIGHT'] = 'true'
    print("\n✓ Playwright mode enabled (no browser windows will open)")
    
    # Initialize database
    print("\nInitializing database...")
    try:
        # Import AFTER setting event loop policy
        from app.db.connection import init_db
        init_db()
        print("   Database initialized successfully!")
    except Exception as e:
        print(f"   Warning: Database initialization issue: {e}")
    
    # Start backend with proper event loop
    backend_process = start_backend()
    if not backend_process:
        print("ERROR: Failed to start backend server")
        return 1
    
    # Start frontend
    frontend_process = start_frontend()
    if not frontend_process:
        print("ERROR: Failed to start frontend server")
        backend_process.terminate()
        return 1
    
    print("\n" + "=" * 60)
    print("Application Started Successfully!")
    print("=" * 60)
    print("\nAccess Points:")
    print("   Web Interface:  http://localhost:3000/unified.html")
    print("   API Docs:       http://localhost:8000/docs")
    print("   API Base:       http://localhost:8000/api/v1")
    print("\nFeatures:")
    print("   ✓ Playwright anti-detection enabled")
    print("   ✓ No browser windows will open")
    print("   ✓ Windows compatibility mode active")
    print("\nTips:")
    print("   - Upload a CSV file through the web interface")
    print("   - Check API documentation for endpoints")
    print("   - Press Ctrl+C to stop both servers")
    
    # Open browser to the CORRECT interface with field mapping
    print("\nOpening browser to unified interface in 3 seconds...")
    time.sleep(3)
    webbrowser.open("http://localhost:3000/unified.html")
    
    try:
        print("\nServers running. Press Ctrl+C to stop...")
        # Keep the script running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nShutting down servers...")
        backend_process.terminate()
        frontend_process.terminate()
        
        # Clean up launcher script
        launcher_path = Path("_uvicorn_launcher.py")
        if launcher_path.exists():
            launcher_path.unlink()
        
        print("Servers stopped successfully!")
        return 0

if __name__ == "__main__":
    sys.exit(main())