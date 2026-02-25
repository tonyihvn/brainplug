"""
TEST: Debug _populate_rag_schema() to identify why only 6 tables are saved instead of 38
"""

from app import app
from backend.services.settings_service import SettingsService
from backend.utils.logger import setup_logger
import logging

logger = setup_logger(__name__)

# Enable detailed logging
logging.basicConfig(level=logging.DEBUG)

def test_populate_rag_schema():
    """Debug the _populate_rag_schema method"""
    
    with app.app_context():
        settings_service = SettingsService()
        
        print("\n" + "="*90)
        print("  DEBUGGING _populate_rag_schema()")
        print("="*90 + "\n")
        
        # Get active database
        active_db = settings_service.get_active_database()
        if not active_db:
            print("[FAIL] No active database")
            return
        
        print(f"Active database: {active_db['name']}\n")
        print(f"Database ID: {active_db['id']}\n")
        
        # Clear existing RAG data first
        print("Clearing existing RAG data...")
        settings_service._wipe_rag_schema(active_db['id'])
        print("[OK] Cleared\n")
        
        # Verify RAG is empty
        before_schemas = settings_service.rag_db.get_all_schemas()
        before_rules = settings_service.rag_db.get_all_rules()
        print(f"Before populate: {len(before_schemas)} schemas, {len(before_rules)} rules\n")
        
        # Now manually call _populate_rag_schema with the active database
        print("Calling _populate_rag_schema()...")
        try:
            settings_service._populate_rag_schema(active_db)
            print("[OK] _populate_rag_schema() completed\n")
        except Exception as e:
            print(f"[FAIL] _populate_rag_schema() failed: {e}\n")
            return
        
        # Check what got saved
        after_schemas = settings_service.rag_db.get_all_schemas()
        after_rules = settings_service.rag_db.get_all_rules()
        
        print(f"After populate: {len(after_schemas)} schemas, {len(after_rules)} rules\n")
        
        # List all schemas
        if after_schemas:
            print("Schemas saved:")
            for schema in after_schemas:
                db_id = schema.get('metadata', {}).get('database_id')
                table = schema.get('metadata', {}).get('table_name')
                print(f"  - {table} (db_id={db_id})")
        else:
            print("No schemas saved!")
        
        print()
        
        # List all rules by type
        if after_rules:
            print("Rules saved:")
            relationships = [r for r in after_rules if r.get('metadata', {}).get('type') == 'relationship']
            sample_data = [r for r in after_rules if r.get('metadata', {}).get('type') == 'sample_data']
            custom = [r for r in after_rules if r.get('metadata', {}).get('type') not in ['relationship', 'sample_data']]
            
            print(f"  Relationships: {len(relationships)}")
            for rule in relationships[:3]:  # Show first 3
                print(f"    - {rule.get('metadata', {}).get('name', 'Unknown')}")
            if len(relationships) > 3:
                print(f"    ... and {len(relationships)-3} more")
            
            print(f"  Sample Data: {len(sample_data)}")
            for rule in sample_data[:3]:  # Show first 3
                print(f"    - {rule.get('metadata', {}).get('name', 'Unknown')}")
            if len(sample_data) > 3:
                print(f"    ... and {len(sample_data)-3} more")
            
            print(f"  Custom Rules: {len(custom)}")
        else:
            print("No rules saved!")

if __name__ == '__main__':
    test_populate_rag_schema()
