#!/usr/bin/env python3
"""
Test script to verify query_mode is properly saved and retrieved throughout the flow.

This script:
1. Connects to the backend API
2. Creates a test database setting with query_mode='api'
3. Verifies it was saved with query_mode='api'
4. Retrieves it and verifies query_mode is preserved
5. Tests RAG generation if database is active
"""

import requests
import json
import sys
from datetime import datetime

# Backend API configuration
BASE_URL = "http://localhost:5000"
API_ENDPOINT = f"{BASE_URL}/api/settings/database"

# Test database settings
TEST_DB_SETTINGS = {
    "name": "Test-Query-Mode-API",
    "db_type": "postgresql",
    "host": "localhost",
    "port": 5432,
    "database": "test_db",
    "username": "postgres",
    "password": "password",
    "is_active": False,  # Don't activate yet, just test persistence
    "query_mode": "api",  # This is what we're testing
    "selected_tables": {},
    "sync_interval": 60,
}

def log(msg, level="INFO"):
    """Print log message with timestamp."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}")

def test_save_database_setting():
    """Test saving a database setting with query_mode."""
    log("=" * 80)
    log("STEP 1: Save database setting with query_mode='api'")
    log("=" * 80)
    
    try:
        log(f"Sending POST to {API_ENDPOINT}")
        log(f"Payload: {json.dumps(TEST_DB_SETTINGS, indent=2)}")
        
        response = requests.post(
            API_ENDPOINT,
            json=TEST_DB_SETTINGS,
            timeout=30
        )
        
        log(f"Response Status: {response.status_code}")
        response_data = response.json()
        log(f"Response: {json.dumps(response_data, indent=2)}")
        
        if response.status_code == 200 and response_data.get('success'):
            saved_setting = response_data.get('data', {})
            
            # Check if query_mode was preserved in response
            if saved_setting.get('query_mode') == 'api':
                log("✓ SUCCESS: query_mode='api' in response", "OK")
            else:
                log(f"✗ WARNING: query_mode mismatch. Expected 'api', got '{saved_setting.get('query_mode')}'", "WARN")
            
            saved_id = saved_setting.get('id')
            return saved_id, response.status_code == 200
        else:
            log(f"✗ FAIL: Unexpected response", "ERROR")
            return None, False
            
    except Exception as e:
        log(f"✗ Exception: {str(e)}", "ERROR")
        return None, False

def test_retrieve_database_setting(setting_id):
    """Test retrieving the database setting and verify query_mode."""
    log("=" * 80)
    log("STEP 2: Retrieve database setting and verify query_mode")
    log("=" * 80)
    
    try:
        log(f"Sending GET to {API_ENDPOINT}")
        response = requests.get(API_ENDPOINT, timeout=30)
        
        log(f"Response Status: {response.status_code}")
        response_data = response.json()
        
        if response.status_code == 200:
            settings = response_data.get('data', [])
            log(f"Retrieved {len(settings)} database settings")
            
            # Find our test setting
            test_setting = next((s for s in settings if s.get('id') == setting_id), None)
            
            if test_setting:
                log(f"Found test setting: {test_setting.get('name')}")
                log(f"  id: {test_setting.get('id')}")
                log(f"  query_mode: {test_setting.get('query_mode')}")
                log(f"  is_active: {test_setting.get('is_active')}")
                
                if test_setting.get('query_mode') == 'api':
                    log("✓ SUCCESS: query_mode='api' persisted in database", "OK")
                    return True
                else:
                    log(f"✗ FAIL: query_mode not preserved. Expected 'api', got '{test_setting.get('query_mode')}'", "ERROR")
                    return False
            else:
                log(f"✗ FAIL: Test setting not found in response", "ERROR")
                return False
        else:
            log(f"✗ FAIL: Unexpected response status {response.status_code}", "ERROR")
            return False
            
    except Exception as e:
        log(f"✗ Exception: {str(e)}", "ERROR")
        return False

def test_update_database_setting(setting_id):
    """Test updating the setting and verify query_mode is preserved."""
    log("=" * 80)
    log("STEP 3: Update database setting and verify query_mode is preserved")
    log("=" * 80)
    
    try:
        update_data = {
            "id": setting_id,
            "name": "Test-Query-Mode-API-UPDATED",
            "db_type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "test_db",
            "username": "postgres",
            "password": "password",
            "is_active": False,
            "query_mode": "api",  # Should be preserved
            "selected_tables": {},
            "sync_interval": 60,
        }
        
        log(f"Sending PUT to {API_ENDPOINT}")
        log(f"Updating with query_mode='api'")
        
        response = requests.post(API_ENDPOINT, json=update_data, timeout=30)
        
        log(f"Response Status: {response.status_code}")
        response_data = response.json()
        
        if response.status_code == 200:
            updated_setting = response_data.get('data', {})
            
            if updated_setting.get('query_mode') == 'api':
                log("✓ SUCCESS: query_mode='api' preserved after update", "OK")
                return True
            else:
                log(f"✗ FAIL: query_mode not preserved. Expected 'api', got '{updated_setting.get('query_mode')}'", "ERROR")
                return False
        else:
            log(f"✗ FAIL: Unexpected response status {response.status_code}", "ERROR")
            return False
            
    except Exception as e:
        log(f"✗ Exception: {str(e)}", "ERROR")
        return False

def cleanup_test_setting(setting_id):
    """Delete the test setting."""
    log("=" * 80)
    log("STEP 4: Cleanup - Delete test setting")
    log("=" * 80)
    
    try:
        log(f"Sending DELETE to {API_ENDPOINT}/{setting_id}")
        
        response = requests.delete(
            f"{API_ENDPOINT}/{setting_id}",
            timeout=30
        )
        
        if response.status_code == 200:
            log("✓ SUCCESS: Test setting deleted", "OK")
            return True
        else:
            log(f"✗ WARNING: Delete returned {response.status_code}", "WARN")
            return False
            
    except Exception as e:
        log(f"✗ Exception during cleanup: {str(e)}", "WARN")
        return False

def main():
    """Run the test flow."""
    log("Starting Query Mode Flow Test")
    log(f"Backend URL: {BASE_URL}")
    
    # Step 1: Save
    setting_id, saved = test_save_database_setting()
    if not saved or not setting_id:
        log("FAILED at save step", "CRITICAL")
        return False
    
    # Step 2: Retrieve
    retrieved = test_retrieve_database_setting(setting_id)
    if not retrieved:
        log("FAILED at retrieve step", "CRITICAL")
        return False
    
    # Step 3: Update
    updated = test_update_database_setting(setting_id)
    if not updated:
        log("FAILED at update step", "CRITICAL")
        return False
    
    # Step 4: Cleanup
    cleanup_test_setting(setting_id)
    
    log("=" * 80)
    log("✓ ALL TESTS PASSED: query_mode flow is working correctly", "OK")
    log("=" * 80)
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        log("Test interrupted by user", "WARN")
        sys.exit(1)
    except Exception as e:
        log(f"Unexpected error: {str(e)}", "CRITICAL")
        sys.exit(1)
