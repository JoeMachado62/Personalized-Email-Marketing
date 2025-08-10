"""
Test script to verify the API upload endpoint works
"""

import requests
import pandas as pd
import json
import time
from pathlib import Path

# Create a test CSV file
test_data = {
    'DEALER NAME': ['Test Motors Inc', 'Sample Auto Sales'],
    'LOCATION ADDRESS': ['123 Main St', '456 Oak Ave'],
    'LOCATION CITY': ['Miami', 'Orlando'],
    'STATE': ['FL', 'FL'],
    'LOC ZIP': ['33101', '32801'],
    'PHONE': ['305-555-0100', '407-555-0200'],
    'EMAIL': ['', ''],  # Empty for enrichment
    'OWNER FIRST NAME': ['', ''],  # Empty for enrichment
    'OWNER LAST NAME': ['', ''],  # Empty for enrichment
}

df = pd.DataFrame(test_data)
test_csv = Path('test_upload.csv')
df.to_csv(test_csv, index=False)
print(f"Created test CSV with {len(df)} records")

# Test the upload endpoint
url = 'http://localhost:8000/api/v1/jobs/upload'

try:
    with open(test_csv, 'rb') as f:
        files = {'file': ('test_dealers.csv', f, 'text/csv')}
        
        print(f"\nUploading to {url}...")
        response = requests.post(url, files=files)
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("Upload successful!")
            print(f"Job ID: {result.get('job_id')}")
            print(f"Status: {result.get('status')}")
            print(f"Total records: {result.get('total_records')}")
            
            # Check job status after a few seconds
            if result.get('job_id'):
                time.sleep(3)
                status_url = f"http://localhost:8000/api/v1/jobs/{result['job_id']}"
                status_response = requests.get(status_url)
                if status_response.status_code == 200:
                    status = status_response.json()
                    print(f"\nJob status after 3 seconds:")
                    print(f"  Status: {status.get('status')}")
                    if status.get('progress'):
                        print(f"  Progress: {status['progress'].get('percentage', 0):.1f}%")
        else:
            print(f"Upload failed: {response.status_code}")
            try:
                error = response.json()
                print(f"Error details: {error}")
            except:
                print(f"Response text: {response.text}")
                
except requests.exceptions.ConnectionError:
    print("Error: Could not connect to API. Make sure the server is running.")
except Exception as e:
    print(f"Error: {e}")
finally:
    # Clean up test file
    if test_csv.exists():
        test_csv.unlink()
        print("\nCleaned up test file")