"""
Comprehensive test for RAG data persistence.
Tests the full flow: Database -> RAG population -> Data persistence -> LLM Settings
"""

import json
import os
from pathlib import Path
from datetime import datetime

# Import Flask app first for context
from app import app

# Import backend modules
from backend.services.settings_service import SettingsService
from backend.utils.rag_database import RAGDatabase
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)

def print_header(title):
    """Print a formatted header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def test_rag_persistence():
    """Test RAG data persistence across operations"""
    
    settings_service = SettingsService()
    rag_db = RAGDatabase()
    
    print_header("RAG DATA PERSISTENCE TEST")
    
    # Test 1: Check database settings
    print("TEST 1: Database Settings")
    print("-" * 80)
    try:
        db_settings = settings_service.get_database_settings()
        print(f"✓ Total database settings: {len(db_settings)}")
        for db in db_settings:
            status = "✓ ACTIVE" if db.get('is_active') else "○ inactive"
            print(f"  {status} | {db['name']} ({db['db_type']}) @ {db.get('host')}")
        print()
    except Exception as e:
        print(f"✗ Error reading database settings: {e}\n")
        return False
    
    # Test 2: Check RAG schemas
    print("TEST 2: RAG Database Schemas")
    print("-" * 80)
    try:
        raw_schemas = rag_db.get_all_schemas()
        formatted_schemas = settings_service.get_rag_schemas()
        
        print(f"✓ Raw schemas from file: {len(raw_schemas)}")
        print(f"✓ Formatted schemas for display: {len(formatted_schemas)}\n")
        
        if raw_schemas:
            print("  Sample schema structure:")
            sample = raw_schemas[0]
            print(f"    ID: {sample.get('id')}")
            print(f"    Content length: {len(sample.get('content', ''))}")
            print(f"    Metadata: {json.dumps(sample.get('metadata', {}), indent=6)}")
            print(f"    Has embedding: {bool(sample.get('embedding'))}\n")
            
            # Group by table
            tables = {}
            for schema in raw_schemas:
                table_name = schema.get('metadata', {}).get('table_name', 'unknown')
                if table_name not in tables:
                    tables[table_name] = 0
                tables[table_name] += 1
            
            print(f"  Schemas by table ({len(tables)} tables):")
            for table, count in sorted(tables.items()):
                print(f"    - {table}: {count} schema entry")
        else:
            print("  ⚠ No schemas found in RAG database\n")
    except Exception as e:
        print(f"✗ Error reading schemas: {e}\n")
        return False
    
    # Test 3: Check RAG business rules
    print("TEST 3: RAG Business Rules (Relationships, Sample Data, Custom Rules)")
    print("-" * 80)
    try:
        raw_rules = rag_db.get_all_rules()
        formatted_rules = settings_service.get_business_rules()
        
        print(f"✓ Raw rules from file: {len(raw_rules)}")
        print(f"✓ Formatted rules for display: {len(formatted_rules)}\n")
        
        # Categorize rules
        categories = {}
        for rule in raw_rules:
            rule_type = rule.get('metadata', {}).get('type', 'unknown')
            if rule_type not in categories:
                categories[rule_type] = []
            categories[rule_type].append(rule)
        
        print("  Rules by type:")
        for rule_type in sorted(categories.keys()):
            count = len(categories[rule_type])
            print(f"    - {rule_type}: {count} rules")
        print()
        
        if raw_rules:
            print("  Sample rule structure:")
            sample = raw_rules[0]
            print(f"    ID: {sample.get('id')}")
            print(f"    Content length: {len(sample.get('content', ''))}")
            print(f"    Metadata: {json.dumps(sample.get('metadata', {}), indent=6)}")
            print(f"    Has embedding: {bool(sample.get('embedding'))}\n")
    except Exception as e:
        print(f"✗ Error reading business rules: {e}\n")
        return False
    
    # Test 4: Verify file storage
    print("TEST 4: RAG Database File Storage")
    print("-" * 80)
    try:
        instance_dir = Path(__file__).parent / 'instance' / 'rag_db'
        schemas_file = instance_dir / 'schemas.json'
        rules_file = instance_dir / 'rules.json'
        
        print(f"  RAG DB directory: {instance_dir}")
        print(f"  Exists: {instance_dir.exists()}\n")
        
        if schemas_file.exists():
            size = schemas_file.stat().st_size
            modified = datetime.fromtimestamp(schemas_file.stat().st_mtime)
            print(f"  ✓ schemas.json")
            print(f"    Size: {size:,} bytes")
            print(f"    Modified: {modified}")
            
            with open(schemas_file, 'r') as f:
                schemas_data = json.load(f)
                print(f"    Items: {len(schemas_data)}\n")
        else:
            print(f"  ⚠ schemas.json not found\n")
        
        if rules_file.exists():
            size = rules_file.stat().st_size
            modified = datetime.fromtimestamp(rules_file.stat().st_mtime)
            print(f"  ✓ rules.json")
            print(f"    Size: {size:,} bytes")
            print(f"    Modified: {modified}")
            
            with open(rules_file, 'r') as f:
                rules_data = json.load(f)
                print(f"    Items: {len(rules_data)}\n")
        else:
            print(f"  ⚠ rules.json not found\n")
    except Exception as e:
        print(f"✗ Error checking file storage: {e}\n")
        return False
    
    # Test 5: Check LLM Settings
    print("TEST 5: LLM Settings")
    print("-" * 80)
    try:
        from backend.models.settings import LLMModel
        from backend.models import db
        
        with app.app_context():
            llm_models = LLMModel.query.all()
            print(f"✓ Total LLM models: {len(llm_models)}")
            
            for model in llm_models:
                status = "✓ ACTIVE" if model.is_active else "○ inactive"
                print(f"  {status} | {model.model_name} ({model.provider}) - {model.model_id}")
            
            if not llm_models:
                print("  ⚠ No LLM models configured\n")
            print()
    except Exception as e:
        print(f"✗ Error reading LLM settings: {e}\n")
        return False
    
    # Test 6: Data counts summary
    print_header("DATA COUNTS SUMMARY")
    try:
        total_db_settings = len(settings_service.get_database_settings())
        total_schemas = len(settings_service.get_rag_schemas())
        total_rules = len(settings_service.get_business_rules())
        
        # Categorize rules
        all_rules = settings_service.get_business_rules()
        relationships = len([r for r in all_rules if r.get('type') == 'relationship'])
        sample_data = len([r for r in all_rules if r.get('type') == 'sample_data'])
        business_rules = len([r for r in all_rules if not r.get('type') or r.get('type') == 'rule'])
        
        print(f"Database Connections:  {total_db_settings}")
        print(f"Schemas:               {total_schemas}")
        print(f"Relationships:         {relationships}")
        print(f"Sample Data Entries:   {sample_data}")
        print(f"Business Rules:        {business_rules}")
        print(f"─" * 40)
        print(f"TOTAL RAG ITEMS:       {total_schemas + total_rules}")
        print()
        
        # Check for data consistency
        print("DATA CONSISTENCY CHECK:")
        if total_db_settings > 0 and total_schemas == 0:
            print("⚠ WARNING: Databases connected but no schemas in RAG!")
            print("   → RAG population may have failed")
        elif total_schemas > 0:
            print("✓ Schemas exist - RAG population successful")
            
            # Check if we have relationships for these schemas
            if relationships < total_schemas:
                print(f"⚠ WARNING: {total_schemas} schemas but only {relationships} relationships")
                print("   → Some relationships may be missing")
            else:
                print("✓ Relationships present for schemas")
            
            if sample_data < total_schemas:
                print(f"⚠ WARNING: {total_schemas} schemas but only {sample_data} sample data entries")
                print("   → Some sample data may be missing")
            else:
                print("✓ Sample data present for schemas")
        else:
            print("○ No RAG data - ensure database is connected and populated")
        
        print()
        return True
        
    except Exception as e:
        print(f"✗ Error in data summary: {e}\n")
        return False

if __name__ == '__main__':
    success = test_rag_persistence()
    print_header("TEST COMPLETE" if success else "TEST FAILED")
    exit(0 if success else 1)
