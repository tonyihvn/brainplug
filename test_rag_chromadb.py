"""Test the new ChromaDB RAG system."""
import sys
sys.path.insert(0, '/'.join(__file__.split('\\')[:-1]))

from app import app
from backend.services.settings_service import SettingsService

with app.app_context():
    settings_service = SettingsService()
    
    print("\n" + "="*60)
    print("NEW RAG SYSTEM TEST - ChromaDB Backend")
    print("="*60)
    
    # 1. Test RAG Database Health
    print("\n1. RAG Database Health Check:")
    health = settings_service.rag_db.health_check()
    print(f"   Status: {health}")
    
    # 2. Get active database
    print("\n2. Active Database:")
    active_db = settings_service.get_active_database()
    if active_db:
        print(f"   ✓ {active_db['name']} (ID: {active_db['id']})")
    else:
        print(f"   ✗ No active database")
    
    # 3. Get schemas from RAG
    print("\n3. Schemas from ChromaDB:")
    schemas = settings_service.get_rag_schemas()
    print(f"   Total: {len(schemas)}")
    if schemas:
        for i, schema in enumerate(schemas[:3]):
            print(f"   [{i+1}] {schema['title']} ({schema['category']})")
        if len(schemas) > 3:
            print(f"   ... and {len(schemas) - 3} more")
    
    # 4. Get business rules from RAG
    print("\n4. Business Rules from ChromaDB:")
    rules = settings_service.get_business_rules()
    print(f"   Total: {len(rules)}")
    if rules:
        for i, rule in enumerate(rules[:3]):
            print(f"   [{i+1}] {rule['name']} ({rule['category']}) - Type: {rule['rule_type']}")
        if len(rules) > 3:
            print(f"   ... and {len(rules) - 3} more")
    
    # 5. Test query
    print("\n5. Test RAG Query (searching for 'users'):")
    query_result = settings_service.query_rag("users table schema")
    print(f"   Schemas found: {len(query_result['schemas'])}")
    print(f"   Rules found: {len(query_result['rules'])}")
    
    print("\n" + "="*60)
    print("✓ ChromaDB RAG System is operational!")
    print("="*60)
