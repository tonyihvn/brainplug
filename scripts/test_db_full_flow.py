import os
import sqlite3
import json
from backend.services.settings_service import SettingsService
from backend.utils.rag_database import RAGDatabase
from backend.utils.database import DatabaseConnector
from backend.utils.conversation_memory import ConversationMemory
from backend.utils.schema_classifier import SchemaClassifier

os.makedirs('instance/store', exist_ok=True)

# Create sqlite DB
db_path = os.path.abspath('instance/store/test_db_full_flow.db')
if os.path.exists(db_path):
    os.remove(db_path)
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute('CREATE TABLE inventories (id INTEGER PRIMARY KEY, category TEXT, name TEXT, created_at TEXT)')
cur.execute("INSERT INTO inventories (category, name, created_at) VALUES ('Laptops', 'Laptop A', '2025-01-01')")
cur.execute("INSERT INTO inventories (category, name, created_at) VALUES ('Laptops', 'Laptop B', '2025-01-02')")
conn.commit()
conn.close()
print('Created sqlite DB at', db_path)

service = SettingsService()
rag = RAGDatabase()

# Prepare database setting payload
setting = {
    'name': 'Full Flow Test DB',
    'db_type': 'sqlite',
    'host': '',
    'port': '',
    'database': db_path,
    'username': '',
    'password': '',
    'is_active': True
}

print('\n1) Saving database setting (active -> should autopopulate)')
res = service.update_database_settings(setting)
print('Saved setting:', json.dumps(res, indent=2))

print('\n2) Listing all database settings from SettingsService.get_database_settings()')
all_settings = service.get_database_settings()
print('Database settings count:', len(all_settings))
for s in all_settings:
    print('-', s.get('id'), s.get('name'))

print('\n3) Checking RAG schemas & rules (may be empty if ChromaDB not available)')
schemas = rag.get_all_schemas()
rules = rag.get_all_rules()
print('RAG schemas:', len(schemas))
print('RAG rules:', len(rules))

print('\n4) Extract schema via DatabaseConnector.get_schema (sanity check)')
conn_str = service._build_connection_string(res)
db_conn = DatabaseConnector()
schema = db_conn.get_schema(conn_str)
print('Extracted tables:', [t['table_name'] for t in schema.get('tables', [])])

print('\n5) Test ConversationMemory + SchemaClassifier context usage')
# Create a ConversationMemory in-memory (no DB conversation object required)
mem = ConversationMemory()
mem.add_message('user', 'Show me the last 20 records in inventories where category is Laptops')
mem.add_message('assistant', "I'll retrieve the last 20 laptop records from the inventories table.", action_data={
    'type': 'DATABASE_QUERY',
    'sql_query': "SELECT * FROM inventories WHERE category='Laptops' ORDER BY created_at DESC LIMIT 20",
    'confidence': 'high'
})
mem.add_message('user', 'Display the result in a table')
mem.add_message('assistant', 'Displayed in table format.', action_data={'type': 'FORMAT_DISPLAY', 'format': 'datatable', 'confidence': 'high'})

last_msgs = mem.get_last_n_messages(5)
print('Last messages (wrapped):')
for m in last_msgs:
    try:
        # support both attribute and dict-style
        role = m.role if hasattr(m, 'role') else m['role']
        content = m.content if hasattr(m, 'content') else m['content']
    except Exception:
        role = str(m)
        content = ''
    print('-', role, ':', content)

classifier = SchemaClassifier()
# Build available_schemas from extracted schema
available_schemas = []
for t in schema.get('tables', []):
    available_schemas.append({'id': f"{t['table_name']}_schema", 'metadata': {'table_name': t['table_name']}})

query = 'Check our previous chat - what tables were we discussing?'
matched, extracted, needs_clarification = classifier.match_tables_to_rag(query, available_schemas, [{'content': m.content, 'role': m.role} for m in last_msgs])
print('\nSchemaClassifier result:')
print('Extracted:', extracted)
print('Matched schemas:', [s['metadata']['table_name'] for s in matched])
print('Needs clarification:', needs_clarification)

print('\n6) Deleting database setting')
del_id = res.get('id')
if del_id:
    ok = service.delete_database_setting(del_id)
    print('Deleted:', ok)
    print('Remaining settings count:', len(service.get_database_settings()))
else:
    print('No id found in saved setting; cannot delete')

print('\nDone.')
