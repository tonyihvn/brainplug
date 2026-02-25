#!/usr/bin/env python3
"""Debug script to check RAG items."""

from backend.services.settings_service import SettingsService
from backend.utils.rag_database import RAGDatabase

service = SettingsService()
rag = RAGDatabase()

# Check database settings
print("=" * 60)
print("DATABASE SETTINGS")
print("=" * 60)
db_settings = service.get_database_settings()
for s in db_settings:
    print(f"\nDatabase: {s.get('name')}")
    print(f"  Type: {s.get('db_type')}")
    print(f"  Host: {s.get('host')}")
    print(f"  Active: {s.get('is_active')}")
    print(f"  ID: {s.get('id')}")

# Check RAG items (schemas)
print("\n" + "=" * 60)
print("RAG SCHEMAS")
print("=" * 60)
schemas = rag.get_all_schemas()
print(f"Total Schemas: {len(schemas)}")
for item in schemas[:10]:
    print(f"  - {item.get('metadata', {}).get('table_name')} (id: {item.get('id')})")

# Check Business Rules
print("\n" + "=" * 60)
print("BUSINESS RULES")
print("=" * 60)
rules = rag.get_all_rules()
print(f"Total Business Rules: {len(rules)}")
for r in rules[:10]:
    print(f"\n  {r.get('metadata', {}).get('rule_name')}")
    print(f"    Type: {r.get('metadata', {}).get('rule_type')}")
    print(f"    Category: {r.get('metadata', {}).get('category')}")
    print(f"    Active: {r.get('metadata', {}).get('is_active')}")
