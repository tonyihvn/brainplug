#!/usr/bin/env python3
"""Test the fixes for chat endpoint and database dropdown."""

import requests
import json

BASE_URL = 'http://127.0.0.1:5000/api'

def test_database_list():
    """Test that database list is returned correctly."""
    print("\n" + "="*60)
    print("TEST 1: Database List (for dropdown)")
    print("="*60)
    
    try:
        response = requests.get(f'{BASE_URL}/settings/database')
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json().get('data', [])
            print(f"[OK] Found {len(data)} database(s)")
            
            for db in data:
                print(f"\n  Database: {db.get('name')}")
                print(f"  ID: {db.get('id')}")
                print(f"  Host: {db.get('host', 'N/A')}")
            
            if len(data) > 0:
                return data[0]['id']
            else:
                print("[!] No databases configured")
                return None
        else:
            print(f"[!] Error: {response.text}")
            return None
    except Exception as e:
        print(f"[!] Exception: {str(e)}")
        return None


def test_chat_endpoint():
    """Test chat endpoint with proper error handling."""
    print("\n" + "="*60)
    print("TEST 2: Chat Endpoint (LLM service check)")
    print("="*60)
    
    try:
        response = requests.post(
            f'{BASE_URL}/chat/message',
            json={'message': 'Hello, how are you?'},
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("[OK] Chat endpoint responded successfully")
            data = response.json().get('data', {})
            print(f"Response: {json.dumps(data, indent=2)[:200]}...")
            return True
        elif response.status_code == 503:
            print("[OK] LLM service not initialized (expected error)")
            print(f"Message: {response.json().get('error')}")
            return True
        else:
            print(f"[!] Error: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"[!] Exception: {str(e)}")
        return False


def test_embedded_data_status(database_id):
    """Test embedded data status endpoint."""
    print("\n" + "="*60)
    print("TEST 3: Embedded Data Status with Sample Data")
    print("="*60)
    
    if not database_id:
        print("[!] No database ID available")
        return False
    
    try:
        response = requests.post(
            f'{BASE_URL}/rag/ingest/status',
            json={'database_id': database_id},
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json().get('data', {})
            print("[OK] Status endpoint responded successfully")
            
            print(f"\n  Database ID: {data.get('database_id')}")
            print(f"  Total Records: {data.get('total_records')}")
            print(f"  Tables Ingested: {data.get('tables_ingested')}")
            print(f"  Storage Path: {data.get('storage_path')}")
            print(f"  Directory Exists: {data.get('exists')}")
            
            ingested_tables = data.get('ingested_tables', [])
            if ingested_tables:
                print(f"\n  Ingested Tables ({len(ingested_tables)}):")
                for table in ingested_tables:
                    print(f"    - {table.get('name')}: {table.get('records_ingested')} records")
            
            sample_embeddings = data.get('sample_embeddings', [])
            if sample_embeddings:
                print(f"\n  Sample Embeddings ({len(sample_embeddings)}):")
                for emb in sample_embeddings:
                    print(f"    - ID: {emb.get('id')}")
                    print(f"      Content: {emb.get('content')[:80]}...")
                    print(f"      Table: {emb.get('table')}")
            else:
                print("\n  [*] No embedded data found yet")
            
            return True
        else:
            print(f"[!] Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"[!] Exception: {str(e)}")
        return False


if __name__ == '__main__':
    print("\n" + "="*60)
    print("Testing Fixes for Chat & Database Dropdown")
    print("="*60)
    
    # Test 1: Get database list
    db_id = test_database_list()
    
    # Test 2: Try chat endpoint
    chat_ok = test_chat_endpoint()
    
    # Test 3: Get embedded data status
    status_ok = test_embedded_data_status(db_id)
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Database List: {'PASS' if db_id else 'FAIL'}")
    print(f"Chat Endpoint: {'PASS' if chat_ok else 'FAIL'}")
    print(f"Embedded Data Status: {'PASS' if status_ok else 'FAIL'}")
    
    if db_id and chat_ok and status_ok:
        print("\n[OK] All tests passed!")
    else:
        print("\n[!] Some tests failed")

