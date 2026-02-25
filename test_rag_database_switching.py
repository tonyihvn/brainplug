#!/usr/bin/env python3
"""Test RAG vector database clearing when switching databases."""

import os
import sys
import sqlite3
import uuid
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app import app
from backend.services.settings_service import SettingsService
from backend.utils.rag_database import RAGDatabase

def create_test_database(db_path, name_suffix):
    """Create a test SQLite database with sample data."""
    if os.path.exists(db_path):
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    if name_suffix == 'db1':
        # Database 1: Users table
        cur.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)')
        cur.execute("INSERT INTO users (name, email) VALUES ('Alice', 'alice@example.com')")
        cur.execute("INSERT INTO users (name, email) VALUES ('Bob', 'bob@example.com')")
        cur.execute('CREATE TABLE profiles (user_id INTEGER PRIMARY KEY, bio TEXT)')
        cur.execute("INSERT INTO profiles (user_id, bio) VALUES (1, 'Software Engineer')")
    else:
        # Database 2: Different schema - Products table
        cur.execute('CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, price REAL)')
        cur.execute("INSERT INTO products (name, price) VALUES ('Laptop', 999.99)")
        cur.execute("INSERT INTO products (name, price) VALUES ('Mouse', 25.99)")
        cur.execute('CREATE TABLE inventory (product_id INTEGER PRIMARY KEY, quantity INTEGER)')
        cur.execute("INSERT INTO inventory (product_id, quantity) VALUES (1, 50)")
    
    conn.commit()
    conn.close()
    print("[OK] Created test database: {}".format(db_path))
    return db_path

def test_rag_database_switching():
    """Test that RAG vector database is cleared when switching databases."""
    with app.app_context():
        print("\n" + "="*80)
        print("Testing RAG Vector Database Clearing on Database Switch")
        print("="*80 + "\n")
        
        # Initialize services
        settings_service = SettingsService()
        rag_db = RAGDatabase()
        
        # Create test databases
        test_dir = project_root / 'instance/test_dbs'
        test_dir.mkdir(parents=True, exist_ok=True)
        
        db1_path = str(test_dir / 'test_db1.db')
        db2_path = str(test_dir / 'test_db2.db')
        
        create_test_database(db1_path, 'db1')
        create_test_database(db2_path, 'db2')
        
        try:
            # Step 1: Activate first database
            print("\n1. Activating first database (Users schema)...")
            db1_setting = {
                'name': 'Test DB 1 - Users',
                'db_type': 'sqlite',
                'host': '',
                'port': '',
                'database': db1_path,
                'username': '',
                'password': '',
                'is_active': True
            }
            
            result1 = settings_service.update_database_settings(db1_setting)
            db1_id = result1.get('id')
            print("   [OK] Database 1 activated: {}".format(result1.get('name')))
            
            # Check RAG schemas after DB1 activation
            schemas_after_db1 = rag_db.get_all_schemas() or []
            print("   [OK] RAG schemas after DB1 activation: {}".format(len(schemas_after_db1)))
            
            # Verify we have users-related tables
            has_users_schema = any('users' in str(s).lower() for s in schemas_after_db1)
            has_profiles_schema = any('profiles' in str(s).lower() for s in schemas_after_db1)
            print("   - Has users schema: {}".format(has_users_schema))
            print("   - Has profiles schema: {}".format(has_profiles_schema))
            
            if has_users_schema and has_profiles_schema:
                print("   [OK] Database 1 schemas correctly populated in RAG")
            else:
                print("   [NOTE] Database 1 may not have been fully populated (schema extraction might be incomplete)")
            
            # Step 2: Activate second database
            print("\n2. Activating second database (Products schema)...")
            db2_setting = {
                'name': 'Test DB 2 - Products',
                'db_type': 'sqlite',
                'host': '',
                'port': '',
                'database': db2_path,
                'username': '',
                'password': '',
                'is_active': True
            }
            
            result2 = settings_service.update_database_settings(db2_setting)
            db2_id = result2.get('id')
            print("   [OK] Database 2 activated: {}".format(result2.get('name')))
            
            # Check RAG schemas after DB2 activation
            schemas_after_db2 = rag_db.get_all_schemas() or []
            print("   [OK] RAG schemas after DB2 activation: {}".format(len(schemas_after_db2)))
            
            # Verify we now have products-related tables and NO users tables
            has_products_schema = any('products' in str(s).lower() for s in schemas_after_db2)
            has_inventory_schema = any('inventory' in str(s).lower() for s in schemas_after_db2)
            still_has_users_schema = any('users' in str(s).lower() for s in schemas_after_db2)
            still_has_profiles_schema = any('profiles' in str(s).lower() for s in schemas_after_db2)
            
            print("   - Has products schema: {}".format(has_products_schema))
            print("   - Has inventory schema: {}".format(has_inventory_schema))
            print("   - Still has users schema: {}".format(still_has_users_schema))
            print("   - Still has profiles schema: {}".format(still_has_profiles_schema))
            
            # Step 3: Verify the clearing worked
            print("\n3. Verification:")
            if still_has_users_schema or still_has_profiles_schema:
                print("   [FAILED] Old database schemas were NOT cleared from RAG")
                print("   This means the RAG vector database still contains data from the previous database")
                return False
            elif has_products_schema and has_inventory_schema:
                print("   [OK] SUCCESS: Old database schemas were cleared from RAG")
                print("   [OK] New database schemas were populated in RAG")
                print("   [OK] RAG now contains only Database 2 data ({} schemas)".format(len(schemas_after_db2)))
                
                # Check that DB1 is deactivated
                all_settings = settings_service.get_database_settings()
                db1_still_active = next((s for s in all_settings if s.get('id') == db1_id and s.get('is_active')), None)
                if db1_still_active:
                    print("   [WARNING] Database 1 is still marked as active")
                    return False
                else:
                    print("   [OK] Database 1 was correctly deactivated")
                
                return True
            else:
                print("   [FAILED] New database schemas were not properly populated")
                return False
            
        except Exception as e:
            print("   [ERROR] Exception during test: {}".format(str(e)))
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            # Cleanup
            print("\n4. Cleanup...")
            try:
                if os.path.exists(db1_path):
                    os.remove(db1_path)
                if os.path.exists(db2_path):
                    os.remove(db2_path)
                print("   [OK] Test databases cleaned up")
            except Exception as e:
                print("   [WARNING] Cleanup error: {}".format(e))

if __name__ == '__main__':
    success = test_rag_database_switching()
    print("\n" + "="*80)
    if success:
        print("[PASS] RAG Database Switch Test PASSED")
        print("The RAG vector database now correctly clears when connecting to a new database")
        sys.exit(0)
    else:
        print("[FAIL] RAG Database Switch Test FAILED")
        sys.exit(1)
