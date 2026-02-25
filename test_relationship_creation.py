"""
TEST: Debug relationship rule creation during RAG population
This will trace through the exact code path and show what's happening
"""

from app import app
from backend.services.settings_service import SettingsService
from backend.utils.logger import setup_logger
import json

logger = setup_logger(__name__)

def test_relationship_creation():
    """Debug relationship creation during RAG population"""
    
    with app.app_context():
        settings_service = SettingsService()
        
        print("\n" + "="*90)
        print("  RELATIONSHIP CREATION DEBUG TEST")
        print("="*90 + "\n")
        
        # Get active database
        active_db = settings_service.get_active_database()
        if not active_db:
            print("✗ No active database")
            return
        
        print(f"Active database: {active_db['name']}\n")
        
        # Get database schema
        from backend.utils.database import DatabaseConnector
        db_connector = DatabaseConnector()
        connection_string = settings_service._build_connection_string(active_db)
        schema_data = db_connector.get_schema(connection_string)
        tables = schema_data.get('tables', [])
        
        print(f"Total tables in database: {len(tables)}\n")
        
        # Check each table for foreign keys
        total_fks = 0
        tables_with_fk = []
        
        for table in tables:
            table_name = table.get('table_name', '')
            fk_entries = table.get('foreign_keys', []) or []
            
            if fk_entries:
                total_fks += len(fk_entries)
                tables_with_fk.append((table_name, len(fk_entries)))
                
                print(f"TABLE: {table_name}")
                print(f"  Foreign Keys: {len(fk_entries)}")
                for fk in fk_entries:
                    constrained = ', '.join(fk.get('constrained_columns', []))
                    referred = fk.get('referred_table', '')
                    referred_cols = ', '.join(fk.get('referred_columns', []) or [])
                    print(f"    - {constrained} → {referred}({referred_cols})")
                print()
        
        print(f"SUMMARY: {total_fks} foreign keys across {len(tables_with_fk)} tables\n")
        
        # Now simulate relationship rule creation
        print("="*90)
        print("  SIMULATING RELATIONSHIP RULE CREATION")
        print("="*90 + "\n")
        
        db_id = active_db['id']
        rag_db = settings_service.rag_db
        rules_created = 0
        rules_failed = 0
        
        for table_name, fk_count in tables_with_fk:
            # Find the table in the schema
            table = next((t for t in tables if t.get('table_name') == table_name), None)
            if not table:
                continue
            
            fk_entries = table.get('foreign_keys', []) or []
            if not fk_entries:
                continue
            
            category = f"{db_id}_{table_name}"
            
            # Build relationship content (same logic as in settings_service.py)
            rel_lines = []
            for fk in fk_entries:
                constrained = ', '.join(fk.get('constrained_columns', []))
                referred = fk.get('referred_table', '')
                referred_cols = ', '.join(fk.get('referred_columns', []) or [])
                if referred_cols:
                    rel_lines.append(f"- {constrained} -> {referred}({referred_cols})")
                else:
                    rel_lines.append(f"- {constrained} -> {referred}")
            
            rel_content = f"Database: {active_db.get('name')}\nTable: {table_name}\n\nRelationships:\n{chr(10).join(rel_lines)}\n\nNote: Auto-generated from foreign key inspection."
            rel_name = f"{active_db.get('name')}_{table_name}_relationships"
            
            print(f"Creating relationship rule for {table_name}...")
            print(f"  Rule name: {rel_name}")
            print(f"  Content preview: {rel_content[:100]}...")
            
            try:
                result = rag_db.add_business_rule(
                    rule_name=rel_name,
                    rule_content=rel_content,
                    db_id=db_id,
                    rule_type="optional",
                    category=category,
                    meta_type="relationship"
                )
                
                if result:
                    print(f"  ✓ Success\n")
                    rules_created += 1
                else:
                    print(f"  ✗ Failed (returned False)\n")
                    rules_failed += 1
            except Exception as e:
                print(f"  ✗ Exception: {e}\n")
                rules_failed += 1
        
        print(f"\nRESULTS:")
        print(f"  Rules created: {rules_created}")
        print(f"  Rules failed: {rules_failed}")
        
        # Verify they were actually saved
        print(f"\n  Verifying saved relationships...")
        all_rules = rag_db.get_all_rules()
        relationships = [r for r in all_rules if r.get('metadata', {}).get('type') == 'relationship']
        print(f"  Total relationship rules in RAG: {len(relationships)}")
        
        if relationships:
            print(f"\n  Sample relationship rule:")
            sample = relationships[0]
            print(f"    ID: {sample.get('id')}")
            print(f"    Content: {sample.get('content', '')[:150]}...")
        else:
            print(f"\n  ⚠️ NO relationship rules found in RAG!")

if __name__ == '__main__':
    test_relationship_creation()
