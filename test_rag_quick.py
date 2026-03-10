#!/usr/bin/env python3
"""Quick test of RAG and database functionality"""
from backend.services.settings_service import SettingsService
from backend.utils.database import DatabaseConnector

# Initialize settings service
settings = SettingsService()

# Check if we have a connected database
db_settings_list = settings.get_database_settings()
print(f'Found {len(db_settings_list)} database settings')

if db_settings_list:
    db_settings = db_settings_list[0]  # Get first active database
    print(f"Database: {db_settings.get('name')}")
    
    # Build connection URL
    db_type = db_settings.get('db_type', 'postgresql')
    host = db_settings.get('host')
    port = db_settings.get('port', 5432)
    database = db_settings.get('database')
    username = db_settings.get('username')
    password = db_settings.get('password')
    
    db_url = f"{db_type}://{username}:{password}@{host}:{port}/{database}"
    print(f"Testing connection to: {db_url.replace(password, '***')}")
    
    try:
        connector = DatabaseConnector()
        schema = connector.get_schema(db_url)
        
        # Schema is returned as {'tables': [...]}
        tables_list = schema.get('tables', [])
        print("[OK] Connection successful!")
        print(f"  Found {len(tables_list)} tables in schema")
        
        # Show first 3 tables with their structure
        for i, table_info in enumerate(tables_list[:3], 1):
            print(f"\n  Table {i}: {type(table_info)}")
            if isinstance(table_info, dict):
                for key in list(table_info.keys())[:3]:
                    print(f"    - {key}: {table_info[key]}")
            else:
                print(f"    - {table_info}")
            
    except Exception as e:
        import traceback
        print(f"[ERROR] Connection failed: {e}")
        traceback.print_exc()
else:
    print("No database configured yet")
