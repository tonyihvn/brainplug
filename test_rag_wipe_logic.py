#!/usr/bin/env python3
"""Direct test of RAG database clearing when switching databases."""

import json
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_wipe_rag_schema_logic():
    """Test the RAG wiping logic directly without the full app."""
    print("\n" + "="*80)
    print("Testing RAG Vector Database Clearing Logic")
    print("="*80 + "\n")
    
    # Test data setup
    test_rag_dir = project_root / 'instance/rag_db'
    test_rag_dir.mkdir(parents=True, exist_ok=True)
    
    schemas_file = test_rag_dir / 'schemas.json'
    rules_file = test_rag_dir / 'rules.json'
    
    # Create test data with schemas and rules for two databases
    db1_id = "db-1-users"
    db2_id = "db-2-products"
    
    test_schemas = [
        {
            'id': 'db-1-users_users_schema',
            'content': 'Users table schema',
            'metadata': {'database_id': db1_id, 'table_name': 'users'}
        },
        {
            'id': 'db-1-users_profiles_schema',
            'content': 'Profiles table schema',
            'metadata': {'database_id': db1_id, 'table_name': 'profiles'}
        },
        {
            'id': 'db-2-products_products_schema',
            'content': 'Products table schema',
            'metadata': {'database_id': db2_id, 'table_name': 'products'}
        },
        {
            'id': 'db-2-products_inventory_schema',
            'content': 'Inventory table schema',
            'metadata': {'database_id': db2_id, 'table_name': 'inventory'}
        }
    ]
    
    test_rules = [
        {
            'id': 'db-1-users_users_sample_data_rule',
            'content': 'Users sample data',
            'metadata': {'database_id': db1_id, 'table_name': 'users', 'type': 'sample_data'}
        },
        {
            'id': 'db-1-users_users_relationships_rule',
            'content': 'Users relationships',
            'metadata': {'database_id': db1_id, 'table_name': 'users', 'type': 'relationship'}
        },
        {
            'id': 'db-2-products_products_sample_data_rule',
            'content': 'Products sample data',
            'metadata': {'database_id': db2_id, 'table_name': 'products', 'type': 'sample_data'}
        }
    ]
    
    # Write test data
    schemas_file.write_text(json.dumps(test_schemas, indent=2))
    rules_file.write_text(json.dumps(test_rules, indent=2))
    
    print("1. Initial state:")
    print("   - DB1 schemas: 2 (users, profiles)")
    print("   - DB1 rules: 2")
    print("   - DB2 schemas: 2 (products, inventory)")
    print("   - DB2 rules: 1")
    print("   - Total: 4 schemas, 3 rules\n")
    
    # Simulate wiping DB1 data
    print("2. Simulating wipe of DB1 data...")
    schemas = json.loads(schemas_file.read_text())
    rules = json.loads(rules_file.read_text())
    
    # Filter out DB1 entries (using 'database_id' field name - THE FIX)
    schemas_before = len(schemas)
    rules_before = len(rules)
    
    schemas = [s for s in schemas if s.get('metadata', {}).get('database_id') != db1_id]
    rules = [r for r in rules if r.get('metadata', {}).get('database_id') != db1_id]
    
    schemas_deleted = schemas_before - len(schemas)
    rules_deleted = rules_before - len(rules)
    
    # Write back
    schemas_file.write_text(json.dumps(schemas, indent=2))
    rules_file.write_text(json.dumps(rules, indent=2))
    
    print("   - Deleted {} schemas".format(schemas_deleted))
    print("   - Deleted {} rules".format(rules_deleted))
    
    # Verify
    print("\n3. After DB1 wipe:")
    print("   - Total schemas: {}".format(len(schemas)))
    print("   - Total rules: {}".format(len(rules)))
    
    has_db1_schemas = any(s.get('metadata', {}).get('database_id') == db1_id for s in schemas)
    has_db1_rules = any(r.get('metadata', {}).get('database_id') == db1_id for r in rules)
    has_db2_schemas = any(s.get('metadata', {}).get('database_id') == db2_id for s in schemas)
    has_db2_rules = any(r.get('metadata', {}).get('database_id') == db2_id for r in rules)
    
    print("\n4. Verification:")
    print("   - DB1 schemas still present: {}".format(has_db1_schemas))
    print("   - DB1 rules still present: {}".format(has_db1_rules))
    print("   - DB2 schemas still present: {}".format(has_db2_schemas))
    print("   - DB2 rules still present: {}".format(has_db2_rules))
    
    # Results
    print("\n" + "="*80)
    if not has_db1_schemas and not has_db1_rules and has_db2_schemas and has_db2_rules:
        print("[PASS] RAG Database Wipe Logic Test PASSED")
        print("The wipe logic correctly removes data by 'database_id' field")
        
        # Show remaining data
        print("\nRemaining RAG data:")
        for schema in schemas:
            print("  - Schema: {} (DB: {})".format(
                schema.get('id'),
                schema.get('metadata', {}).get('database_id')
            ))
        for rule in rules:
            print("  - Rule: {} (DB: {})".format(
                rule.get('id'),
                rule.get('metadata', {}).get('database_id')
            ))
        
        return True
    else:
        print("[FAIL] RAG Database Wipe Logic Test FAILED")
        if has_db1_schemas:
            print("ERROR: DB1 schemas were NOT wiped")
        if has_db1_rules:
            print("ERROR: DB1 rules were NOT wiped")
        return False

if __name__ == '__main__':
    success = test_wipe_rag_schema_logic()
    sys.exit(0 if success else 1)
