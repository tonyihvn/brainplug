#!/usr/bin/env python3
"""
Test script for Foreign Key and Indexes feature.
Tests the new API endpoints for discovering table relationships.
"""

import requests
import json
from typing import Dict, Any

BASE_URL = "http://127.0.0.1:5000"

def test_discover_tables_with_fk():
    """Test that discover_tables now returns foreign keys and indexes."""
    print("\n" + "="*80)
    print("TEST 1: Discover Tables with Foreign Keys and Indexes")
    print("="*80)
    
    # First get the database settings to get a valid database_id
    response = requests.get(f"{BASE_URL}/api/settings/database")
    if response.status_code != 200:
        print("✗ Could not get database settings")
        return False
    
    databases = response.json().get('data', [])
    if not databases:
        print("✗ No databases configured")
        return False
    
    db_id = databases[0].get('id')
    print(f"Using database: {db_id}")
    
    # Call discover_tables endpoint
    response = requests.post(
        f"{BASE_URL}/api/settings/database/discover-tables",
        json={"database_id": db_id}
    )
    
    if response.status_code != 200:
        print(f"✗ Failed to discover tables: {response.text}")
        return False
    
    data = response.json().get('data', [])
    print(f"✓ Discovered {len(data)} tables")
    
    # Check that tables have the new fields
    if data:
        table = data[0]
        print(f"\nSample table: {table.get('name')}")
        print(f"  - Columns: {len(table.get('columns', []))} columns")
        print(f"  - Foreign Keys: {len(table.get('foreign_keys', []))} foreign keys")
        print(f"  - Indexes: {len(table.get('indexes', []))} indexes")
        print(f"  - Primary Keys: {table.get('primary_keys', [])}")
        
        # Show foreign keys if any
        fks = table.get('foreign_keys', [])
        if fks:
            print(f"\n  Foreign Key Relationships:")
            for fk in fks:
                print(f"    - {fk.get('column')} → {fk.get('references_table')}.{fk.get('references_column')}")
        
        # Show indexes if any
        indexes = table.get('indexes', [])
        if indexes:
            print(f"\n  Indexes:")
            for idx in indexes:
                print(f"    - {idx.get('name')} on {idx.get('columns')}")
        
        # Validate structure
        if 'foreign_keys' in table and 'indexes' in table and 'primary_keys' in table:
            print("\n✓ Table structure includes all required fields")
            return True
        else:
            print("\n✗ Table structure missing required fields")
            return False
    
    return False

def test_table_relationships():
    """Test the new table-relationships endpoint."""
    print("\n" + "="*80)
    print("TEST 2: Get Table Relationships")
    print("="*80)
    
    # Get database settings
    response = requests.get(f"{BASE_URL}/api/settings/database")
    if response.status_code != 200:
        print("✗ Could not get database settings")
        return False
    
    databases = response.json().get('data', [])
    if not databases:
        print("✗ No databases configured")
        return False
    
    db_id = databases[0].get('id')
    
    # First discover tables to get a table with relationships
    response = requests.post(
        f"{BASE_URL}/api/settings/database/discover-tables",
        json={"database_id": db_id}
    )
    
    if response.status_code != 200:
        print(f"✗ Failed to discover tables")
        return False
    
    tables = response.json().get('data', [])
    if not tables:
        print("✗ No tables found")
        return False
    
    # Try to find a table with foreign keys
    test_table = None
    for table in tables:
        if table.get('foreign_keys') or any(r.get('references_table') == table.get('name') for r in 
                                            sum([t.get('foreign_keys', []) for t in tables], [])):
            test_table = table
            break
    
    if not test_table:
        print("ℹ No tables with relationships found, using first table")
        test_table = tables[0]
    
    table_name = test_table.get('name')
    print(f"Testing relationships for table: {table_name}")
    
    # Call table-relationships endpoint
    response = requests.post(
        f"{BASE_URL}/api/settings/database/table-relationships",
        json={"database_id": db_id, "table_name": table_name}
    )
    
    if response.status_code != 200:
        print(f"✗ Failed to get relationships: {response.text}")
        return False
    
    relationships = response.json().get('data', {})
    print(f"\n✓ Retrieved relationships for {table_name}")
    print(f"  - Tables this one references: {len(relationships.get('references', []))}")
    print(f"  - Tables that reference this: {len(relationships.get('referenced_by', []))}")
    print(f"  - Total tables in database: {len(relationships.get('all_tables', []))}")
    
    # Show references
    references = relationships.get('references', [])
    if references:
        print(f"\n  References (foreign keys pointing outward):")
        for ref in references:
            print(f"    - {ref.get('local_column')} → {ref.get('table')}.{ref.get('remote_column')}")
    
    # Show referenced_by
    referenced_by = relationships.get('referenced_by', [])
    if referenced_by:
        print(f"\n  Referenced By (other tables pointing here):")
        for ref in referenced_by:
            print(f"    - {ref.get('table')}.{ref.get('local_column')} ← {ref.get('remote_column')}")
    
    # Validate structure
    if 'references' in relationships and 'referenced_by' in relationships and 'all_tables' in relationships:
        print("\n✓ Relationships structure is valid")
        return True
    else:
        print("\n✗ Relationships structure is invalid")
        return False

def main():
    """Run all tests."""
    print("\n" + "#"*80)
    print("# FOREIGN KEY AND INDEX DISCOVERY TEST SUITE")
    print("#"*80)
    
    results = []
    
    try:
        results.append(("Discover Tables with FK/Indexes", test_discover_tables_with_fk()))
    except Exception as e:
        print(f"✗ Exception in test_discover_tables_with_fk: {e}")
        results.append(("Discover Tables with FK/Indexes", False))
    
    try:
        results.append(("Table Relationships Endpoint", test_table_relationships()))
    except Exception as e:
        print(f"✗ Exception in test_table_relationships: {e}")
        results.append(("Table Relationships Endpoint", False))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)
    print(f"\nTotal: {total_passed}/{total_tests} tests passed")
    
    return all(passed for _, passed in results)

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
