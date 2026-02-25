"""
COMPREHENSIVE RAG PERSISTENCE TEST & DIAGNOSTIC REPORT
======================================================

This script tests all database, LLM, and RAG operations to identify issues.
"""

from app import app
from backend.services.settings_service import SettingsService
from backend.services.llm_service import LLMService
from backend.utils.rag_database import RAGDatabase
from backend.models.settings import LLMModel
from backend.models import db
from backend.utils.logger import setup_logger
import json

logger = setup_logger(__name__)

def print_section(title):
    print(f"\n{'='*90}")
    print(f"  {title}")
    print(f"{'='*90}\n")

def print_subsection(title):
    print(f"\n{title}")
    print(f"{'-'*90}\n")

def test_all_systems():
    """Comprehensive test of all systems"""
    
    with app.app_context():
        settings_service = SettingsService()
        rag_db = RAGDatabase()
        
        print_section("COMPREHENSIVE RAG PERSISTENCE TEST REPORT")
        
        # ==================== DATABASE SETTINGS ====================
        print_subsection("1. DATABASE SETTINGS")
        
        db_settings = settings_service.get_database_settings()
        print(f"Total configured: {len(db_settings)}")
        
        for db_setting in db_settings:
            print(f"\n  Database: {db_setting['name']}")
            print(f"    Type: {db_setting['db_type']}")
            print(f"    Host: {db_setting.get('host', 'N/A')}:{db_setting.get('port', 'N/A')}")
            print(f"    Database: {db_setting['database']}")
            print(f"    Status: {'✓ ACTIVE' if db_setting.get('is_active') else '○ Inactive'}")
            print(f"    ID: {db_setting['id']}")
        
        # ==================== RAG DATABASE STATUS ====================
        print_subsection("2. RAG DATABASE STATUS")
        
        schemas = settings_service.get_rag_schemas()
        rules = settings_service.get_business_rules()
        
        print(f"Schemas stored: {len(schemas)}")
        print(f"Business rules stored: {len(rules)}")
        
        # Analyze schemas
        if schemas:
            print(f"\n  Schemas by database:")
            db_map = {}
            for schema in schemas:
                db_id = schema.get('metadata', {}).get('database_id', 'unknown')
                if db_id not in db_map:
                    db_map[db_id] = []
                db_map[db_id].append(schema.get('title', 'unknown'))
            
            for db_id, schema_list in db_map.items():
                db_name = next((d['name'] for d in db_settings if d['id'] == db_id), 'Unknown')
                print(f"    {db_name} ({len(schema_list)} tables): {', '.join(schema_list)}")
        
        # Analyze rules by type
        print(f"\n  Business rules by type:")
        relationships = [r for r in rules if r.get('type') == 'relationship']
        sample_data = [r for r in rules if r.get('type') == 'sample_data']
        custom_rules = [r for r in rules if not r.get('type') or r.get('type') == 'rule']
        
        print(f"    - Relationships: {len(relationships)}")
        print(f"    - Sample Data: {len(sample_data)}")
        print(f"    - Custom Rules: {len(custom_rules)}")
        
        # ==================== DATABASE SCHEMA ANALYSIS ====================
        print_subsection("3. DATABASE SCHEMA ANALYSIS (Current vs RAG)")
        
        active_db = settings_service.get_active_database()
        if active_db:
            print(f"Active database: {active_db['name']}")
            
            try:
                # Get actual schema from database
                from backend.utils.database import DatabaseConnector
                db_connector = DatabaseConnector()
                connection_string = settings_service._build_connection_string(active_db)
                actual_schema = db_connector.get_schema(connection_string)
                actual_tables = actual_schema.get('tables', [])
                
                # Count foreign keys
                total_fks = sum(len(t.get('foreign_keys', [])) for t in actual_tables)
                
                print(f"\nDatabase statistics:")
                print(f"  Total tables in database: {len(actual_tables)}")
                print(f"  Total foreign keys in database: {total_fks}")
                
                # Compare with RAG
                rag_schemas = [s for s in schemas if s.get('metadata', {}).get('database_id') == active_db['id']]
                print(f"  Schemas in RAG: {len(rag_schemas)}")
                
                if len(actual_tables) > len(rag_schemas):
                    print(f"\n  ⚠️ ISSUE: Only {len(rag_schemas)}/{len(actual_tables)} tables documented in RAG")
                    print(f"     Missing tables: {set(t['table_name'] for t in actual_tables) - set(s['title'] for s in rag_schemas)}")
                
                if total_fks > 0 and len(relationships) == 0:
                    print(f"\n  ⚠️ ISSUE: Database has {total_fks} foreign keys but 0 relationships in RAG")
                    print(f"     Some tables with FK: {[t['table_name'] for t in actual_tables if t.get('foreign_keys')][:5]}")
                
            except Exception as e:
                print(f"  ✗ Error analyzing schema: {e}")
        else:
            print(f"No active database")
        
        # ==================== LLM SETTINGS ====================
        print_subsection("4. LLM SETTINGS")
        
        llm_models = LLMModel.query.all()
        print(f"Total LLM models: {len(llm_models)}")
        
        for model in llm_models:
            status = "✓ ACTIVE" if model.is_active else "○"
            print(f"  {status} {model.model_id} ({model.provider})")
        
        # ==================== FILE STORAGE ====================
        print_subsection("5. FILE STORAGE (Persistence Check)")
        
        from pathlib import Path
        from datetime import datetime
        
        instance_dir = Path(__file__).parent / 'instance' / 'rag_db'
        schemas_file = instance_dir / 'schemas.json'
        rules_file = instance_dir / 'rules.json'
        
        for file_path, label in [(schemas_file, 'schemas.json'), (rules_file, 'rules.json')]:
            if file_path.exists():
                stat = file_path.stat()
                modified = datetime.fromtimestamp(stat.st_mtime)
                print(f"\n  ✓ {label}")
                print(f"    Size: {stat.st_size:,} bytes")
                print(f"    Modified: {modified}")
            else:
                print(f"\n  ✗ {label} NOT FOUND")
        
        # ==================== ISSUE ANALYSIS ====================
        print_section("IDENTIFIED ISSUES & ROOT CAUSES")
        
        issues = []
        
        # Issue 1: Incomplete table coverage
        if active_db and 'actual_tables' in locals():
            if len(rag_schemas) < len(actual_tables):
                issues.append({
                    'severity': 'HIGH',
                    'title': 'Incomplete RAG Schema Coverage',
                    'description': f'{len(actual_tables) - len(rag_schemas)} tables not documented in RAG',
                    'cause': 'Database may have been updated/refreshed, wiping RAG data',
                    'impact': 'LLM has incomplete knowledge of database structure'
                })
        
        # Issue 2: Missing relationships
        if total_fks > 0 and len(relationships) == 0:
            issues.append({
                'severity': 'CRITICAL',
                'title': 'Zero Relationship Rules Generated',
                'description': f'Database has {total_fks} foreign keys but no relationship rules',
                'cause': 'Relationship rule creation during RAG population may be failing silently',
                'impact': 'LLM cannot understand table relationships and joins'
            })
        
        # Issue 3: Data disappears on refresh
        if len(db_settings) > 0 and len(schemas) < 5:
            issues.append({
                'severity': 'HIGH',
                'title': 'RAG Data Disappears on Database Refresh',
                'description': f'Only {len(schemas)} schemas stored after database operations',
                'cause': 'Deactivation/reactivation cycle may be wiping RAG data incorrectly',
                'impact': 'Users lose RAG knowledge when updating database settings'
            })
        
        if issues:
            for i, issue in enumerate(issues, 1):
                print(f"\nISSUE #{i}: {issue['title']}")
                print(f"  Severity: {issue['severity']}")
                print(f"  Description: {issue['description']}")
                print(f"  Root Cause: {issue['cause']}")
                print(f"  Impact: {issue['impact']}")
        else:
            print("\n✓ No critical issues detected")
        
        # ==================== RECOMMENDATIONS ====================
        print_section("RECOMMENDATIONS")
        
        print("""
1. PROTECT RAG DATA DURING DATABASE UPDATES
   - Don't wipe RAG data on simple parameter updates
   - Only wipe if user explicitly deletes the database
   - Implement 'UPDATE' vs 'DELETE' operations separately

2. ENSURE ALL TABLES ARE DOCUMENTED
   - Log which tables are being processed and saved
   - Verify foreign keys are detected in your database schema
   - Add error handling for individual table failures

3. TEST RELATIONSHIP DETECTION
   - Enable debugging in _populate_rag_schema()
   - Log each FK found and each relationship rule created
   - Verify FK detection works with your MySQL version

4. IMPLEMENT RAG DATA VERSIONING
   - Keep track of when RAG was last updated
   - Warn user before wiping
   - Provide backup/restore functionality

5. ADD REFRESH FUNCTIONALITY
   - Let users explicitly refresh RAG without losing data
   - Add incremental population for new tables only
   - Show progress and completion status
        """)
        
        print_section("END OF REPORT")
        print(f"\nGenerated: {datetime.now()}")

if __name__ == '__main__':
    test_all_systems()
