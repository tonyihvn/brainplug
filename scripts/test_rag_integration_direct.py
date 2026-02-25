import os
import sqlite3
from backend.utils.database import DatabaseConnector
from backend.utils.rag_database import RAGDatabase

os.makedirs('instance/store', exist_ok=True)

# Create sqlite DB
db_path = os.path.abspath('instance/store/test_integration_direct.db')
if os.path.exists(db_path):
    os.remove(db_path)
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)')
cur.execute("INSERT INTO users (name, email) VALUES ('Alice', 'alice@example.com')")
cur.execute("INSERT INTO users (name, email) VALUES ('Bob', 'bob@example.com')")
conn.commit()
conn.close()

print('Created test sqlite DB at', db_path)

# Build connection string
connection_string = f"sqlite:///{db_path}"
print('Using connection string:', connection_string)

# Inspect schema
db_connector = DatabaseConnector()
schema = db_connector.get_schema(connection_string)
print('Extracted schema tables:', [t['table_name'] for t in schema.get('tables', [])])

# Add to RAG via RAGDatabase
rag = RAGDatabase()
db_id = 'test_sqlite_direct'

schemas_added = 0
rules_added = 0
for table in schema.get('tables', []):
    table_name = table.get('table_name')
    cols = table.get('columns', [])
    field_descriptions = []
    for col in cols:
        sample_values = col.get('sample_values', [])
        sample_str = ', '.join(str(v) for v in sample_values[:3]) if sample_values else 'no sample data'
        field_descriptions.append(f"- {col['name']} ({col['type']}): {sample_str}")
    schema_content = f"Table: {table_name}\n\nColumns:\n{chr(10).join(field_descriptions)}"

    added = rag.add_schema(table_name=table_name, schema_content=schema_content, db_id=db_id)
    if added:
        schemas_added += 1
        print('Added schema for', table_name)

    rule_name = f"{db_id}_{table_name}_rule"
    rule_content = f"Auto-generated rule for {table_name}"
    if rag.add_business_rule(rule_name=rule_name, rule_content=rule_content, db_id=db_id, rule_type='optional', category=f"{db_id}_{table_name}", meta_type='sample_data'):
        rules_added += 1
        print('Added rule for', table_name)

print('Schemas added:', schemas_added)
print('Rules added:', rules_added)

print('Health:', rag.health_check())

print('Listing saved schemas:')
all_schemas = rag.get_all_schemas()
for s in all_schemas:
    print('-', s.get('id'), s.get('metadata', {}).get('table_name'))

print('Test finished.')
