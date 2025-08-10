#!/usr/bin/env python3
"""
Setup verification script for AI Sales Agent MVP.
Checks all dependencies and configuration.
"""

import sys
import os
from pathlib import Path

def check_python_version():
    """Check Python version is 3.8+"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        return False, f"Python 3.8+ required, found {version.major}.{version.minor}"
    return True, f"Python {version.major}.{version.minor}.{version.micro}"

def check_imports():
    """Check all required imports work"""
    required_imports = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("pandas", "Pandas"),
        ("httpx", "HTTPX"),
        ("playwright", "Playwright"),
        ("dotenv", "Python-dotenv"),
        ("pydantic", "Pydantic"),
        ("aiofiles", "Aiofiles"),
        ("openai", "OpenAI SDK"),
    ]
    
    results = []
    for module, name in required_imports:
        try:
            __import__(module)
            results.append((True, f"{name} [OK]"))
        except ImportError:
            results.append((False, f"{name} [MISSING] - Run: pip install {module}"))
    
    return results

def check_env_file():
    """Check .env file exists and has required keys"""
    env_path = Path(".env")
    if not env_path.exists():
        return False, ".env file not found - Copy .env.example to .env"
    
    with open(env_path) as f:
        content = f.read()
    
    if "your-openai-api-key-here" in content:
        return False, ".env file exists but LLM_API_KEY not configured"
    
    if "LLM_API_KEY=" in content:
        return True, ".env file configured"
    
    return False, ".env file missing LLM_API_KEY"

def check_directories():
    """Check required directories exist"""
    dirs = ["app", "auto_enrich", "frontend", "data", "uploads", "outputs"]
    results = []
    
    for dir_name in dirs:
        path = Path(dir_name)
        if path.exists():
            results.append((True, f"{dir_name}/ [OK]"))
        else:
            path.mkdir(exist_ok=True)
            results.append((True, f"{dir_name}/ [CREATED]"))
    
    return results

def check_database():
    """Check database initialization"""
    try:
        from app.db.connection import init_db
        init_db()
        return True, "Database initialized"
    except Exception as e:
        return False, f"Database error: {e}"

def main():
    print("AI Sales Agent MVP - Setup Verification")
    print("=" * 50)
    
    # Check Python version
    success, msg = check_python_version()
    print(f"Python Version: {msg}")
    if not success:
        print("X Please upgrade Python")
        sys.exit(1)
    
    print("\nDependencies:")
    imports = check_imports()
    all_good = True
    for success, msg in imports:
        print(f"  {msg}")
        if not success:
            all_good = False
    
    if not all_good:
        print("\nX Missing dependencies. Run:")
        print("   pip install -r requirements.txt")
        print("   playwright install chromium")
        sys.exit(1)
    
    print("\nDirectories:")
    dirs = check_directories()
    for success, msg in dirs:
        print(f"  {msg}")
    
    print("\nConfiguration:")
    success, msg = check_env_file()
    print(f"  {msg}")
    if not success:
        print("\nX Please configure .env file:")
        print("   1. Copy .env.example to .env")
        print("   2. Add your OpenAI API key")
        sys.exit(1)
    
    print("\nDatabase:")
    success, msg = check_database()
    print(f"  {msg}")
    if not success:
        print("X Database initialization failed")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("All checks passed! Your system is ready.")
    print("\nNext steps:")
    print("1. Start the server: uvicorn app.main:app --reload")
    print("2. Open browser: http://localhost:8000")
    print("3. Upload a CSV file to test enrichment")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())