#!/usr/bin/env python3
"""
Test script to diagnose RAG generation issues.

This script tests:
1. Database connection is working
2. Schema extraction finds tables
3. RAG items are being created
4. Response includes correct statistics

It tests with a real database connection if credentials are provided.
"""

import requests
import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Backend API configuration
BASE_URL = "http://localhost:5000"
API_ENDPOINT = f"{BASE_URL}/api/settings/database"

# PostgreSQL test database (adjust as needed)
# These can be environment variables
PG_HOST = os.getenv('TEST_PG_HOST', 'localhost')
PG_PORT = os.getenv('TEST_PG_PORT', '5432')
PG_USER = os.getenv('TEST_PG_USER', 'postgres')
PG_PASSWORD = os.getenv('TEST_PG_PASSWORD', 'postgres')
PG_DATABASE = os.getenv('TEST_PG_DATABASE', 'postgres')

# For testing without a real database, use SQLite
# Create a simple SQLite test database
SQLITE_DB_PATH = Path(__file__).parent.parent / "instance" / "test_rag_gen.db"

TEST_DB_SETTINGS_SQLITE = {
    "name": "SQLite-Test-RAG",
    "db_type": "sqlite",
    "database": str(SQLITE_DB_PATH),
    "is_active": True,  # Activate to trigger RAG generation
    "query_mode": "direct",
}

TEST_DB_SETTINGS_POSTGRES = {
    "name": "PostgreSQL-Test-RAG",
    "db_type": "postgresql",
    "host": PG_HOST,
    "port": int(PG_PORT),
    "database": PG_DATABASE,
    "username": PG_USER,
    "password": PG_PASSWORD,
    "is_active": True,
    "query_mode": "direct",
}

def log(msg, level="INFO"):
    """Print log message with timestamp."""
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # Include milliseconds
    color_codes = {
        "OK": "\033[92m",      # Green
        "WARN": "\033[93m",    # Yellow
        "ERROR": "\033[91m",   # Red
        "CRITICAL": "\033[91m", # Red
        "INFO": "\033[94m",    # Blue
    }
    reset = "\033[0m"
    color = color_codes.get(level, "")
    print(f"{color}[{ts}] [{level:8}]{reset} {msg}")

def create_sqlite_db():
    """Create a simple SQLite test database with some tables."""
    import sqlite3
    
    SQLITE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Remove old test database if exists
    if SQLITE_DB_PATH.exists():
        SQLITE_DB_PATH.unlink()
        log(f"Removed existing test database: {SQLITE_DB_PATH}", "INFO")
    
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        
        # Create sample tables
        cursor.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                total REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE products (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                price REAL,
                stock INTEGER DEFAULT 0
            )
        ''')
        
        # Insert some sample data
        cursor.execute("INSERT INTO users (name, email) VALUES ('John Doe', 'john@example.com')")
        cursor.execute("INSERT INTO users (name, email) VALUES ('Jane Smith', 'jane@example.com')")
        cursor.execute("INSERT INTO products (name, price, stock) VALUES ('Widget A', 9.99, 100)")
        cursor.execute("INSERT INTO products (name, price, stock) VALUES ('Widget B', 19.99, 50)")
        cursor.execute("INSERT INTO orders (user_id, total) VALUES (1, 29.98)")
        
        conn.commit()
        conn.close()
        
        log(f"✓ Created SQLite test database with 3 tables at: {SQLITE_DB_PATH}", "OK")
        return True
    except Exception as e:
        log(f"✗ Failed to create SQLite database: {str(e)}", "ERROR")
        return False

def test_rag_generation(use_sqlite=True):
    """Test RAG generation with database settings."""
    log("=" * 100)
    log("RAG GENERATION TEST", "INFO")
    log("=" * 100)
    
    # Create test database setup
    if use_sqlite:
        if not create_sqlite_db():
            return False
        test_settings = TEST_DB_SETTINGS_SQLITE
    else:
        test_settings = TEST_DB_SETTINGS_POSTGRES
    
    log(f"Testing with: {test_settings['name']} ({test_settings['db_type']})", "INFO")
    
    try:
        # Step 1: Save database setting with is_active=True
        log("STEP 1: Save database setting with is_active=True", "INFO")
        log(f"Sending POST to {API_ENDPOINT}", "INFO")
        log(f"Payload: name={test_settings['name']}, db_type={test_settings['db_type']}, is_active=True", "INFO")
        
        response = requests.post(API_ENDPOINT, json=test_settings, timeout=60)
        
        log(f"Response Status: {response.status_code}", "INFO")
        response_data = response.json()
        
        if response.status_code != 200:
            log(f"✗ FAIL: Unexpected response status", "ERROR")
            log(f"Response: {json.dumps(response_data, indent=2)}", "ERROR")
            return False
        
        if not response_data.get('success'):
            log(f"✗ FAIL: success=false in response", "ERROR")
            return False
        
        saved_setting = response_data.get('data', {})
        setting_id = saved_setting.get('id')
        
        log(f"✓ Setting saved with id: {setting_id}", "OK")
        
        # Step 2: Check RAG statistics
        log("STEP 2: Check RAG generation statistics", "INFO")
        
        rag_stats = saved_setting.get('rag_statistics', {})
        log(f"RAG Statistics: {json.dumps(rag_stats, indent=2)}", "INFO")
        
        status = rag_stats.get('status')
        tables_scanned = rag_stats.get('tables_scanned', 0)
        items_created = rag_stats.get('items_created', 0)
        
        log(f"  Status: {status}", "INFO")
        log(f"  Tables Scanned: {tables_scanned}", "INFO")
        log(f"  Items Created: {items_created}", "INFO")
        log(f"  Mapping: {rag_stats.get('mapping', 'N/A')}", "INFO")
        log(f"  Storage: {rag_stats.get('storage', 'N/A')}", "INFO")
        
        # Analyze results
        log("STEP 3: Analyze results", "INFO")
        
        if status == 'failed':
            error_msg = rag_stats.get('error', 'Unknown error')
            log(f"✗ FAIL: RAG generation failed with error: {error_msg}", "ERROR")
            return False
        elif status != 'success':
            log(f"✗ FAIL: Unexpected status: {status}", "ERROR")
            return False
        
        if tables_scanned == 0:
            log(f"✗ WARNING: No tables scanned! This is the core issue.", "WARN")
            log(f"Expected to find at least 3 tables (users, orders, products)", "WARN")
            return False
        
        if items_created == 0:
            log(f"✗ WARNING: No RAG items created despite finding {tables_scanned} tables!", "WARN")
            return False
        
        log(f"✓ SUCCESS: RAG generation completed successfully", "OK")
        log(f"  Found {tables_scanned} tables and created {items_created} RAG items", "OK")
        
        # Step 4: Retrieve setting and verify it's active
        log("STEP 4: Verify setting is still active", "INFO")
        
        response = requests.get(API_ENDPOINT, timeout=30)
        settings_list = response.json().get('data', [])
        retrieved = next((s for s in settings_list if s.get('id') == setting_id), None)
        
        if retrieved:
            log(f"Retrieved setting: is_active={retrieved.get('is_active')}", "INFO")
            if not retrieved.get('is_active'):
                log(f"✗ WARNING: Setting is no longer active!", "WARN")
        
        return True
        
    except Exception as e:
        log(f"✗ Exception: {str(e)}", "ERROR")
        import traceback
        log(f"Traceback: {traceback.format_exc()}", "ERROR")
        return False
    finally:
        # Cleanup will happen automatically (settings are not permanently saved for tests)
        pass

def check_backend_health():
    """Check if backend is running."""
    log("Checking backend health...", "INFO")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            log(f"✓ Backend is healthy", "OK")
            return True
    except Exception:
        pass
    
    log(f"⚠ Backend might not be running at {BASE_URL}", "WARN")
    log(f"Make sure the Flask app is running: python app.py", "WARN")
    return False

def main():
    """Run the tests."""
    log("Starting RAG Generation Diagnostic Test", "INFO")
    log(f"Backend URL: {BASE_URL}", "INFO")
    
    if not check_backend_health():
        log("Cannot proceed without backend", "CRITICAL")
        return False
    
    # Test with SQLite (no external DB needed)
    log("", "INFO")
    success = test_rag_generation(use_sqlite=True)
    
    log("", "INFO")
    log("=" * 100)
    if success:
        log("✓ ALL TESTS PASSED", "OK")
        log("RAG generation is working correctly", "OK")
    else:
        log("✗ TESTS FAILED", "CRITICAL")
        log("Review the logs above to identify the issue", "CRITICAL")
    log("=" * 100)
    
    return success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        log("", "INFO")
        log("Test interrupted by user", "WARN")
        sys.exit(1)
    except Exception as e:
        log(f"Unexpected error: {str(e)}", "CRITICAL")
        import traceback
        log(traceback.format_exc(), "ERROR")
        sys.exit(1)
