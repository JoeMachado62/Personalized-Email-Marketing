#!/usr/bin/env python3
"""
Integration test for the complete AI Sales Agent MVP.
Tests the full pipeline from CSV upload to enriched download.
"""

import asyncio
import pandas as pd
import httpx
import time
from pathlib import Path
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings

# Test configuration
API_BASE_URL = "http://localhost:8000/api/v1"
TEST_DATA_PATH = Path("test_data")
TEST_DATA_PATH.mkdir(exist_ok=True)


def create_test_csv(num_records=10):
    """Create a test CSV file with sample dealer data."""
    data = {
        "Company Name": [f"Test Dealer {i}" for i in range(1, num_records + 1)],
        "Address": [f"{100+i} Main St, Miami, FL 33101" for i in range(num_records)],
        "Phone": [f"305-555-{1000+i:04d}" for i in range(num_records)],
        "Email": [f"info@dealer{i}.com" for i in range(1, num_records + 1)],
        "Contact Name": [f"John Smith {i}" for i in range(1, num_records + 1)]
    }
    
    df = pd.DataFrame(data)
    csv_path = TEST_DATA_PATH / f"test_dealers_{num_records}.csv"
    df.to_csv(csv_path, index=False)
    return csv_path


async def test_health_check():
    """Test API health endpoint."""
    print("🔍 Testing health check...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("✅ Health check passed")
        return True


async def test_file_upload(csv_path):
    """Test CSV file upload."""
    print(f"📤 Testing file upload with {csv_path.name}...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        with open(csv_path, "rb") as f:
            files = {"file": (csv_path.name, f, "text/csv")}
            response = await client.post(
                f"{API_BASE_URL}/jobs/upload",
                files=files
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"
        print(f"✅ File uploaded successfully. Job ID: {data['job_id']}")
        return data["job_id"]


async def test_job_status(job_id):
    """Test job status tracking."""
    print(f"📊 Monitoring job {job_id}...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        max_attempts = 60  # 5 minutes max
        for attempt in range(max_attempts):
            response = await client.get(f"{API_BASE_URL}/jobs/{job_id}")
            assert response.status_code == 200
            
            data = response.json()
            status = data["status"]
            progress = data.get("progress", {})
            
            print(f"  Status: {status} | Progress: {progress.get('processed_records', 0)}/{progress.get('total_records', 0)}")
            
            if status == "completed":
                print("✅ Job completed successfully")
                return True
            elif status == "failed":
                print(f"❌ Job failed: {data.get('error_message', 'Unknown error')}")
                return False
            
            await asyncio.sleep(5)  # Wait 5 seconds before next check
        
        print("⏱️ Job timed out")
        return False


async def test_download_results(job_id):
    """Test downloading enriched results."""
    print(f"📥 Downloading results for job {job_id}...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test CSV download
        response = await client.get(f"{API_BASE_URL}/jobs/{job_id}/download?format=csv")
        assert response.status_code == 200
        
        # Save the CSV
        output_path = TEST_DATA_PATH / f"enriched_{job_id}.csv"
        with open(output_path, "wb") as f:
            f.write(response.content)
        
        # Verify the CSV
        df = pd.read_csv(output_path)
        assert len(df) > 0
        
        # Check for enriched columns
        expected_columns = ["Website", "Subject Line", "Email Body"]
        for col in expected_columns:
            assert any(col in c for c in df.columns), f"Missing column: {col}"
        
        print(f"✅ Results downloaded successfully to {output_path}")
        print(f"  Records enriched: {len(df)}")
        
        # Test JSON download
        response = await client.get(f"{API_BASE_URL}/jobs/{job_id}/download?format=json")
        assert response.status_code == 200
        json_data = response.json()
        assert "enriched_records" in json_data
        
        return output_path


async def test_job_history():
    """Test job history endpoint."""
    print("📜 Testing job history...")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/jobs?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        print(f"✅ Job history retrieved: {len(data['jobs'])} jobs found")
        return True


async def test_concurrent_jobs():
    """Test multiple concurrent job processing."""
    print("🔄 Testing concurrent job processing...")
    
    # Create multiple test files
    csv_files = [create_test_csv(5) for _ in range(3)]
    
    # Upload all files concurrently
    async with httpx.AsyncClient(timeout=30.0) as client:
        upload_tasks = []
        for csv_path in csv_files:
            with open(csv_path, "rb") as f:
                files = {"file": (csv_path.name, f.read(), "text/csv")}
                task = client.post(f"{API_BASE_URL}/jobs/upload", files=files)
                upload_tasks.append(task)
        
        responses = await asyncio.gather(*upload_tasks)
        job_ids = [r.json()["job_id"] for r in responses]
        
    print(f"✅ Created {len(job_ids)} concurrent jobs")
    
    # Monitor all jobs
    status_tasks = [test_job_status(job_id) for job_id in job_ids]
    results = await asyncio.gather(*status_tasks)
    
    success_count = sum(1 for r in results if r)
    print(f"✅ Concurrent processing: {success_count}/{len(job_ids)} jobs succeeded")
    
    return success_count == len(job_ids)


async def run_integration_tests():
    """Run complete integration test suite."""
    print("🚀 Starting AI Sales Agent MVP Integration Tests")
    print("=" * 50)
    
    try:
        # Test 1: Health Check
        await test_health_check()
        print()
        
        # Test 2: Small file upload and processing
        csv_path = create_test_csv(10)
        job_id = await test_file_upload(csv_path)
        print()
        
        # Test 3: Job status monitoring
        success = await test_job_status(job_id)
        if not success:
            print("❌ Job processing failed")
            return False
        print()
        
        # Test 4: Download results
        await test_download_results(job_id)
        print()
        
        # Test 5: Job history
        await test_job_history()
        print()
        
        # Test 6: Concurrent processing
        await test_concurrent_jobs()
        print()
        
        print("=" * 50)
        print("✅ All integration tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False


async def run_performance_test(num_records=100):
    """Run performance test with specified number of records."""
    print(f"⚡ Running performance test with {num_records} records")
    print("=" * 50)
    
    # Create test data
    csv_path = create_test_csv(num_records)
    
    # Upload and process
    start_time = time.time()
    job_id = await test_file_upload(csv_path)
    
    # Monitor until completion
    success = await test_job_status(job_id)
    
    if success:
        end_time = time.time()
        duration = end_time - start_time
        
        # Download and analyze results
        output_path = await test_download_results(job_id)
        df = pd.read_csv(output_path)
        
        # Calculate metrics
        records_per_minute = (num_records / duration) * 60
        cost_estimate = num_records * 0.015  # Estimated $0.015 per record
        
        print("=" * 50)
        print("📊 Performance Metrics:")
        print(f"  Total records: {num_records}")
        print(f"  Processing time: {duration:.2f} seconds")
        print(f"  Records/minute: {records_per_minute:.1f}")
        print(f"  Estimated cost: ${cost_estimate:.2f}")
        print(f"  Success rate: {(len(df)/num_records)*100:.1f}%")
        
        return True
    
    return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Sales Agent MVP Integration Tests")
    parser.add_argument("--performance", type=int, help="Run performance test with N records")
    parser.add_argument("--concurrent", action="store_true", help="Run concurrent job tests")
    args = parser.parse_args()
    
    if args.performance:
        asyncio.run(run_performance_test(args.performance))
    elif args.concurrent:
        asyncio.run(test_concurrent_jobs())
    else:
        asyncio.run(run_integration_tests())