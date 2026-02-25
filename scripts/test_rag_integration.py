import os
import sqlite3
from backend.services.settings_service import SettingsService
from backend.utils.rag_database import RAGDatabase

# Ensure instance directories
os.makedirs('instance/store', exist_ok=True)
os.makedirs('instance/rag_db', exist_ok=True)

# Create a small sqlite database with one table
db_path = os.path.abspath('instance/store/test_integration.db')
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

# Prepare database setting payload
setting = {
    'name': 'Test Sqlite DB',
    'db_type': 'sqlite',
    'host': '',
    'port': '',
    'database': db_path,
    'username': '',
    'password': '',
    'is_active': True
}

service = SettingsService()
rag = RAGDatabase()

print('Saving database setting via SettingsService.update_database_settings...')
res = service.update_database_settings(setting)
print('Update returned:', res)

print('Checking RAG schemas and rules...')
schemas = rag.get_all_schemas()
rules = rag.get_all_rules()
print('Schemas count:', len(schemas))
print('Rules count:', len(rules))

if schemas:
    print('Sample schema metadata:', schemas[0].get('metadata'))
if rules:
    print('Sample rule metadata:', rules[0].get('metadata'))

print('Integration script finished.')
