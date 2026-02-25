"""
Detailed database schema analysis - check for foreign keys
"""

from app import app
from backend.utils.database import DatabaseConnector
from backend.services.settings_service import SettingsService
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)

def analyze_database_schema():
    """Analyze database schema for foreign keys and relationships"""
    
    settings_service = SettingsService()
    db_connector = DatabaseConnector()
    
    print("\n" + "="*80)
    print("  DATABASE SCHEMA ANALYSIS")
    print("="*80 + "\n")
    
    # Get active database
    active_db = settings_service.get_active_database()
    if not active_db:
        print("✗ No active database configured\n")
        return False
    
    print(f"Database: {active_db['name']} ({active_db['db_type']})")
    print(f"Host: {active_db['host']}:{active_db['port']}")
    print(f"Database: {active_db['database']}\n")
    
    try:
        # Build connection string and get schema
        connection_string = settings_service._build_connection_string(active_db)
        schema = db_connector.get_schema(connection_string)
        
        tables = schema.get('tables', [])
        print(f"Total tables: {len(tables)}\n")
        
        for table in tables:
            table_name = table.get('table_name')
            columns = table.get('columns', [])
            foreign_keys = table.get('foreign_keys', [])
            primary_keys = table.get('primary_keys', [])
            
            print(f"TABLE: {table_name}")
            print(f"  Primary Key: {', '.join(primary_keys) if primary_keys else 'None'}")
            print(f"  Columns: {len(columns)}")
            print(f"  Foreign Keys: {len(foreign_keys)}")
            
            if foreign_keys:
                print(f"  Foreign Key Details:")
                for fk in foreign_keys:
                    constrained = ', '.join(fk.get('constrained_columns', []))
                    referred_table = fk.get('referred_table', 'unknown')
                    referred_cols = ', '.join(fk.get('referred_columns', []) or [])
                    print(f"    - {constrained} → {referred_table}({referred_cols})")
            
            print()
        
        # Summary
        total_fks = sum(len(t.get('foreign_keys', [])) for t in tables)
        print(f"\nSUMMARY:")
        print(f"  Total tables: {len(tables)}")
        print(f"  Total foreign keys: {total_fks}")
        
        if total_fks == 0:
            print(f"\n⚠ WARNING: No foreign keys found in database!")
            print(f"   → This explains why NO relationship rules are being created")
            print(f"   → Database may not have defined relationships")
        
        return True
        
    except Exception as e:
        print(f"✗ Error analyzing schema: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    with app.app_context():
        success = analyze_database_schema()
        exit(0 if success else 1)
