#!/usr/bin/env python3
"""Test manual ingestion endpoints."""

import requests
import json
from pathlib import Path

BASE_URL = 'http://127.0.0.1:5000/api'

def test_manual_ingest():
    """Test the manual ingestion endpoint."""
    print("\n" + "="*60)
    print("TEST 1: Manual Ingestion Trigger")
    print("="*60)
    
    # First, let's get the database ID
    print("\n1. Getting database settings...")
    response = requests.get(f'{BASE_URL}/settings/database')
    if response.status_code == 200:
        databases = response.json().get('data', [])
        if databases:
            db_id = databases[0]['id']
            print(f"   [OK] Found database: {db_id}")
            print(f"   - Name: {databases[0].get('name', 'N/A')}")
            print(f"   - Connection: {databases[0].get('connection_string', 'N/A')[:50]}...")
        else:
            print("   [!] No databases found. Please configure a database first.")
            return False
    else:
        print(f"   [!] Error: {response.status_code} - {response.text}")
        return False
    
    # Test manual ingestion
    print("\n2. Testing /api/rag/ingest/manual endpoint...")
    payload = {'database_id': db_id}
    try:
        response = requests.post(f'{BASE_URL}/rag/ingest/manual', json=payload, timeout=30)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("   [OK] Manual ingestion endpoint responded successfully!")
            print(f"   Response: {json.dumps(data, indent=2)}")
            return True
        elif response.status_code == 404:
            print("   [!] Endpoint not found (404)")
            print(f"   Response: {response.text}")
            return False
        else:
            print(f"   [!] Error: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except requests.exceptions.Timeout:
        print("   [!] Request timed out (30 seconds)")
        return False
    except Exception as e:
        print(f"   [!] Exception: {str(e)}")
        return False


def test_ingest_status():
    """Test the ingestion status endpoint."""
    print("\n" + "="*60)
    print("TEST 2: Ingestion Status Check")
    print("="*60)
    
    # Get database ID
    print("\n1. Getting database settings...")
    response = requests.get(f'{BASE_URL}/settings/database')
    if response.status_code == 200:
        databases = response.json().get('data', [])
        if databases:
            db_id = databases[0]['id']
            print(f"   [OK] Using database: {db_id}")
        else:
            print("   [!] No databases found.")
            return False
    else:
        print(f"   [!] Error: {response.status_code}")
        return False
    
    # Test status endpoint
    print("\n2. Testing /api/rag/ingest/status endpoint...")
    payload = {'database_id': db_id}
    try:
        response = requests.post(f'{BASE_URL}/rag/ingest/status', json=payload, timeout=10)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("   [OK] Status endpoint responded successfully!")
            
            status_data = data.get('data', {})
            print(f"\n   Ingestion Status:")
            print(f"   - Database ID: {status_data.get('database_id', 'N/A')}")
            print(f"   - Total Records: {status_data.get('total_records', 0)}")
            print(f"   - Tables Ingested: {status_data.get('tables_ingested', 0)}")
            print(f"   - Storage Path: {status_data.get('storage_path', 'N/A')}")
            print(f"   - Exists: {status_data.get('exists', False)}")
            
            tables = status_data.get('ingested_tables', [])
            if tables:
                print(f"\n   Ingested Tables:")
                for table in tables:
                    print(f"     - {table.get('name', 'N/A')}: {table.get('records_ingested', 0)} records")
            
            return True
        else:
            print(f"   [!] Error: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"   [!] Exception: {str(e)}")
        return False


def check_endpoints_exist():
    """Check if the new endpoints exist in app.py and TypeScript files."""
    print("\n" + "="*60)
    print("TEST 0: Verification - Check if endpoints exist")
    print("="*60)
    
    app_file = Path('app.py')
    data_ingest_file = Path('components/settings/DataIngestionSettings.tsx')
    gemini_service_file = Path('services/geminiService.ts')
    
    checks = [
        (app_file, '/rag/ingest/manual', 'Backend: POST /api/rag/ingest/manual'),
        (app_file, '/rag/ingest/status', 'Backend: POST /api/rag/ingest/status'),
        (data_ingest_file, 'triggerManualIngestion', 'Frontend: triggerManualIngestion function'),
        (data_ingest_file, 'checkIngestedDataStatus', 'Frontend: checkIngestedDataStatus function'),
        (gemini_service_file, 'triggerManualIngestion', 'API: triggerManualIngestion method'),
        (gemini_service_file, 'getIngestionStatus', 'API: getIngestionStatus method'),
    ]
    
    print("\nChecking for required endpoints and functions:")
    all_found = True
    for file_path, pattern, description in checks:
        if not file_path.exists():
            print(f"   [!] File not found: {file_path}")
            all_found = False
            continue
        
        try:
            # Read with UTF-8 encoding, ignore errors
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            if pattern in content:
                print(f"   [OK] Found: {description}")
            else:
                print(f"   [!] Missing: {description}")
                all_found = False
        except Exception as e:
            print(f"   [!] Error reading {file_path}: {str(e)}")
            all_found = False
    
    return all_found


if __name__ == '__main__':
    print("\n" + "="*60)
    print("Manual Ingestion Feature - Endpoint Tests")
    print("="*60)
    
    # Check endpoints exist
    if not check_endpoints_exist():
        print("\n[!] Some endpoints or functions are missing!")
        exit(1)
    
    # Test the endpoints
    test1_passed = test_manual_ingest()
    test2_passed = test_ingest_status()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Manual Ingestion Endpoint: {'PASS' if test1_passed else 'FAIL'}")
    print(f"Status Endpoint: {'PASS' if test2_passed else 'FAIL'}")
    
    if test1_passed and test2_passed:
        print("\n[OK] All tests passed!")
        exit(0)
    else:
        print("\n[!] Some tests failed!")
        exit(1)
