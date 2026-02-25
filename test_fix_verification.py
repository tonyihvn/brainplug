"""
TEST: Verify that the rule_id fix allows all 12 relationship rules to be created
"""

from app import app
from backend.services.settings_service import SettingsService

def test_rule_creation():
    """Test that all rules are created correctly"""
    
    with app.app_context():
        settings_service = SettingsService()
        
        print("\n" + "="*80)
        print("VERIFY FIX: Rule ID Duplication")
        print("="*80 + "\n")
        
        # Get active database
        active_db = settings_service.get_active_database()
        if not active_db:
            print("[FAIL] No active database")
            return
        
        # Get all current rules
        all_rules = settings_service.rag_db.get_all_rules()
        relationships = [r for r in all_rules if r.get('metadata', {}).get('type') == 'relationship']
        sample_data = [r for r in all_rules if r.get('metadata', {}).get('type') == 'sample_data']
        
        print(f"Database: {active_db['name']}\n")
        print(f"Total rules in RAG: {len(all_rules)}")
        print(f"  - Relationship rules: {len(relationships)}")
        print(f"  - Sample data rules: {len(sample_data)}\n")
        
        # List all relationship rules
        if relationships:
            print("Relationship Rules (should match tables with foreign keys):")
            for rel in sorted(relationships, key=lambda x: x.get('metadata', {}).get('name', '')):
                table = rel.get('metadata', {}).get('name', 'Unknown')
                # Extract table name by removing prefix/suffix
                if 'Iventory_' in table and '_relationships' in table:
                    table = table.replace('Iventory_', '').replace('_relationships', '')
                print(f"  - {table}")
            print()
        
        # Expected relationship tables (those with foreign keys)
        from backend.utils.database import DatabaseConnector
        db_connector = DatabaseConnector()
        connection_string = settings_service._build_connection_string(active_db)
        schema_data = db_connector.get_schema(connection_string)
        tables = schema_data.get('tables', [])
        
        tables_with_fk = [t.get('table_name') for t in tables if t.get('foreign_keys')]
        print(f"Expected relationship tables (in database): {len(tables_with_fk)}")
        for t in sorted(tables_with_fk):
            print(f"  - {t}")
        
        print("\n" + "="*80)
        print("VERIFICATION RESULT:")
        print("="*80)
        
        rel_table_names = set(
            r.get('metadata', {}).get('name', '').replace('Iventory_', '').replace('_relationships', '')
            for r in relationships
        )
        
        expected = set(tables_with_fk)
        missing = expected - rel_table_names
        extra = rel_table_names - expected - {''}
        
        if not missing and not extra:
            print("[PASS] All relationship rules created correctly!")
            print(f"  Expected: {len(expected)} relationship rules")
            print(f"  Created:  {len(relationships)} relationship rules")
        else:
            print("[FAIL] Relationship rules incomplete")
            if missing:
                print(f"  Missing: {missing}")
            if extra:
                print(f"  Extra:   {extra}")

if __name__ == '__main__':
    test_rule_creation()
