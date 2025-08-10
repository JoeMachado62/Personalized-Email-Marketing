#!/usr/bin/env python3
"""
Test script to verify AI Sales Agent installation.
This script checks all components and dependencies.
"""

import sys
import sqlite3
from pathlib import Path

def test_imports():
    """Test that all required packages can be imported"""
    print("Testing package imports...")
    
    try:
        import fastapi
        print(f"[OK] FastAPI {fastapi.__version__}")
    except ImportError:
        print("[ERROR] FastAPI not found")
        return False
    
    try:
        import uvicorn
        print(f"[OK] Uvicorn {uvicorn.__version__}")
    except ImportError:
        print("[ERROR] Uvicorn not found")
        return False
    
    try:
        import pandas
        print(f"[OK] Pandas {pandas.__version__}")
    except ImportError:
        print("[ERROR] Pandas not found")
        return False
    
    try:
        import pydantic
        print(f"[OK] Pydantic {pydantic.__version__}")
    except ImportError:
        print("[ERROR] Pydantic not found")
        return False
    
    try:
        import aiofiles
        print(f"[OK] AIOFiles (installed)")
    except ImportError:
        print("[ERROR] AIOFiles not found")
        return False
    
    return True

def test_app_structure():
    """Test that application structure is correct"""
    print("\nTesting application structure...")
    
    required_files = [
        "app/__init__.py",
        "app/main.py",
        "app/config.py",
        "app/models/__init__.py",
        "app/models/job.py",
        "app/api/__init__.py",
        "app/api/jobs.py",
        "app/api/health.py",
        "app/db/__init__.py",
        "app/db/connection.py",
        "requirements.txt"
    ]
    
    all_exist = True
    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            print(f"[OK] {file_path}")
        else:
            print(f"[ERROR] {file_path} not found")
            all_exist = False
    
    return all_exist

def test_directories():
    """Test that required directories exist"""
    print("\nTesting directory structure...")
    
    required_dirs = [
        "uploads",
        "outputs",
        "data"
    ]
    
    all_exist = True
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        if dir_path.exists() and dir_path.is_dir():
            print(f"[OK] {dir_name}/ directory")
        else:
            print(f"[ERROR] {dir_name}/ directory not found")
            all_exist = False
    
    return all_exist

def test_database():
    """Test database initialization"""
    print("\nTesting database...")
    
    try:
        from app.db.connection import init_db
        init_db()
        print("[OK] Database initialization successful")
        
        # Test database connection
        from app.db.connection import get_db
        with get_db() as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            expected_tables = ['jobs', 'records', 'enrichment_cache', 'email_templates', 'api_usage', 'settings']
            missing_tables = set(expected_tables) - set(tables)
            
            if not missing_tables:
                print("[OK] All database tables created")
                print(f"  Tables: {', '.join(tables)}")
            else:
                print(f"[ERROR] Missing tables: {missing_tables}")
                return False
        
        return True
    
    except Exception as e:
        print(f"[ERROR] Database test failed: {e}")
        return False

def test_config():
    """Test configuration loading"""
    print("\nTesting configuration...")
    
    try:
        from app.config import settings
        print("[OK] Configuration loaded")
        print(f"  App Name: {settings.APP_NAME}")
        print(f"  Version: {settings.VERSION}")
        print(f"  Upload Dir: {settings.UPLOAD_DIR}")
        print(f"  Output Dir: {settings.OUTPUT_DIR}")
        print(f"  Max File Size: {settings.MAX_FILE_SIZE_MB}MB")
        print(f"  Max Records: {settings.MAX_RECORDS_PER_JOB}")
        
        if settings.LLM_API_KEY:
            print("[OK] LLM API Key configured")
        else:
            print("[WARN] LLM API Key not set (this is okay for testing)")
        
        return True
    
    except Exception as e:
        print(f"[ERROR] Configuration test failed: {e}")
        return False

def test_api_models():
    """Test API models"""
    print("\nTesting API models...")
    
    try:
        from app.models.job import JobStatus, JobCreate, JobResponse
        
        # Test enum
        assert JobStatus.PENDING == "pending"
        print("[OK] JobStatus enum working")
        
        # Test model creation
        job_create = JobCreate(options={"test": "value"})
        print("[OK] JobCreate model working")
        
        job_response = JobResponse(
            job_id="test-123",
            status="pending",
            message="Test job",
            total_records=100
        )
        print("[OK] JobResponse model working")
        
        return True
    
    except Exception as e:
        print(f"[ERROR] API models test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("AI Sales Agent Installation Test")
    print("=" * 40)
    
    tests = [
        ("Package Imports", test_imports),
        ("App Structure", test_app_structure),
        ("Directories", test_directories),
        ("Database", test_database),
        ("Configuration", test_config),
        ("API Models", test_api_models)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 20)
        
        try:
            if test_func():
                passed += 1
                print(f"[PASS] {test_name}")
            else:
                print(f"[FAIL] {test_name}")
        except Exception as e:
            print(f"[FAIL] {test_name} - Exception: {e}")
    
    print("\n" + "=" * 40)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("All tests passed! Installation is complete.")
        print("\nTo start the server, run:")
        print("  python run_server.py")
        return True
    else:
        print("Some tests failed. Please check the installation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)