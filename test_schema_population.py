#!/usr/bin/env python3
"""Test script to verify RAG schema auto-population."""

import requests
import json
import time

BASE_URL = 'http://127.0.0.1:5000'

def test_sqlite_schema_population():
    """Test schema population with SQLite database."""
    print("=" * 60)
    print("Testing RAG Schema Auto-Population")
    print("=" * 60)
    
    # Test with SQLite (uses app.db which has tables from the app)
    print("\n1. Connecting to SQLite database (app.db)...")
    payload = {
        'name': 'App SQLite Database',
        'db_type': 'sqlite',
        'database': 'instance/app.db',  # Use the instance folder
        'is_active': True
    }
    
    response = requests.post(f'{BASE_URL}/api/settings/database', json=payload)
    print(f"   Response Status: {response.status_code}")
    result = response.json()
    print(f"   Response: {json.dumps(result, indent=2)}")
    
    if response.status_code != 200:
        print("   ❌ Failed to connect to database")
        return False
    
    db_id = result['data'].get('id')
    print(f"   ✅ Database saved with ID: {db_id}")
    
    # Wait a moment for schema population to complete
    print("\n2. Waiting for schema auto-population...")
    time.sleep(2)
    
    # Get schemas
    print("\n3. Fetching auto-populated schemas...")
    response = requests.get(f'{BASE_URL}/api/rag/schema')
    print(f"   Response Status: {response.status_code}")
    schemas = response.json()
    print(f"   Response: {json.dumps(schemas, indent=2)}")
    
    # Get business rules
    print("\n4. Fetching auto-generated business rules...")
    response = requests.get(f'{BASE_URL}/api/rag/business-rules')
    print(f"   Response Status: {response.status_code}")
    rules = response.json()
    print(f"   Total Rules: {rules.get('data', {}).get('total', 0)}")
    print(f"   Auto-generated Rules: {rules.get('data', {}).get('auto_generated_count', 0)}")
    
    if rules.get('data', {}).get('auto_generated_count', 0) > 0:
        print("   ✅ Business rules were auto-generated!")
        print(f"   Rules (first 3): {json.dumps(rules.get('data', {}).get('rules', [])[:3], indent=2)}")
        return True
    else:
        print("   ⚠️  No business rules were auto-generated")
        return False

if __name__ == '__main__':
    try:
        success = test_sqlite_schema_population()
        print("\n" + "=" * 60)
        if success:
            print("✅ Test PASSED: Schema auto-population works!")
        else:
            print("⚠️  Test indicated potential issues - check logs")
        print("=" * 60)
    except Exception as e:
        print(f"❌ Test FAILED with error: {e}")
        import traceback
        traceback.print_exc()
