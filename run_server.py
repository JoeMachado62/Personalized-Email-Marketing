#!/usr/bin/env python3
"""
Simple startup script for the AI Sales Agent MVP.
Starts both the backend API and serves the frontend.
"""

import os
import sys
import subprocess
import time
import webbrowser
from pathlib import Path

def check_port(port):
    """Check if a port is available"""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', port))
    sock.close()
    return result != 0  # True if port is available

def start_backend():
    """Start the FastAPI backend server"""
    print("Starting FastAPI backend server on port 8000...")
    
    # Check if port 8000 is available
    if not check_port(8000):
        print("WARNING: Port 8000 is already in use!")
        print("   Try: netstat -ano | findstr :8000")
        return None
    
    # Start uvicorn in a subprocess
    cmd = [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
    process = subprocess.Popen(cmd)
    
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
    print("AI Sales Agent MVP - Starting Application")
    print("=" * 60)
    
    # Initialize database
    print("\nInitializing database...")
    try:
        from app.db.connection import init_db
        init_db()
        print("   Database initialized successfully!")
    except Exception as e:
        print(f"   Warning: Database initialization issue: {e}")
    
    # Start backend
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
    print("   Web Interface:  http://localhost:3000")
    print("   API Docs:       http://localhost:8000/docs")
    print("   API Base:       http://localhost:8000/api/v1")
    print("\nTips:")
    print("   - Upload a CSV file through the web interface")
    print("   - Check API documentation for endpoints")
    print("   - Press Ctrl+C to stop both servers")
    
    # Open browser
    print("\nOpening browser in 3 seconds...")
    time.sleep(3)
    webbrowser.open("http://localhost:3000")
    
    try:
        print("\nServers running. Press Ctrl+C to stop...")
        # Keep the script running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nShutting down servers...")
        backend_process.terminate()
        frontend_process.terminate()
        print("Servers stopped successfully!")
        return 0

if __name__ == "__main__":
    sys.exit(main())