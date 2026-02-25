# RAG Vector Database Clearing on Database Switch

## Overview
When you connect to a different database, the RAG vector database automatically clears all data from the previous database and populates it with data from the newly connected database. This ensures data consistency and prevents information from multiple databases from being mixed in the vector store.

## How It Works

### 1. Database Activation Flow
When a database is activated (set as `is_active=True`):

```
POST /api/settings/database with is_active=True
  ↓
update_database_settings()
  ↓
  [If activating a NEW database]
  ├─ 1. Find any previously active database
  ├─ 2. Wipe RAG entries for the old database
  ├─ 3. Deactivate the old database
  ├─ 4. Populate RAG with new database schema
  └─ 5. Update .env DATABASE_URL
  ↓
RAG is now populated ONLY with new database structure
```

### 2. Implementation Details

#### In `backend/services/settings_service.py`

The `update_database_settings()` method now handles database switching:

**For Existing Database Updates:**
```python
if not was_active and is_now_active:
    # Find and deactivate any other active database
    for other_setting in all_settings:
        if other_setting.get('is_active') and other_setting.get('id') != existing_id:
            # Wipe RAG entries for the old database
            self._wipe_rag_schema(old_db_id)
            # Deactivate the old database
            other_setting['is_active'] = False
            self.rag_db.save_database_setting(old_db_id, other_setting)
    
    # Populate RAG with new database schema
    self._populate_rag_schema(updated)
```

**For New Database Creation:**
```python
if is_active:
    # Find and deactivate any currently active database
    for other_setting in all_settings:
        if other_setting.get('is_active') and other_setting.get('id') != new_id:
            self._wipe_rag_schema(old_db_id)
            other_setting['is_active'] = False
            self.rag_db.save_database_setting(old_db_id, other_setting)
    
    # Populate RAG with new database schema
    self._populate_rag_schema(new_setting)
```

#### The `_wipe_rag_schema()` Method

This method removes all RAG entries associated with a specific database:

```python
def _wipe_rag_schema(self, database_id: str):
    """Remove RAG entries for a specific database when it's deactivated."""
    try:
        logger.info(f"Wiping RAG entries for database: {database_id}")
        
        schemas_deleted = 0
        rules_deleted = 0
        
        # Remove schemas for this database
        schemas = self.rag_db.get_all_schemas() or []
        for schema in schemas:
            # Check both 'db_id' (legacy) and 'database_id' (current)
            schema_metadata = schema.get('metadata', {})
            if schema_metadata.get('database_id') == database_id or schema_metadata.get('db_id') == database_id:
                if self.rag_db.delete_schema(schema.get('id')):
                    schemas_deleted += 1
        
        # Remove business rules for this database
        rules = self.rag_db.get_all_rules() or []
        for rule in rules:
            # Check both 'db_id' (legacy) and 'database_id' (current)
            rule_metadata = rule.get('metadata', {})
            if rule_metadata.get('database_id') == database_id or rule_metadata.get('db_id') == database_id:
                if self.rag_db.delete_rule(rule.get('id')):
                    rules_deleted += 1
        
        logger.info(f"[OK] Wiped RAG entries for database: {database_id} (Schemas: {schemas_deleted}, Rules: {rules_deleted})")
    except Exception as e:
        logger.error(f"Error wiping RAG schema: {str(e)}")
```

## Key Fix: Metadata Field Name

### The Problem
The RAG database stores schemas and rules with a `database_id` field in their metadata:

```python
metadata = {
    'table_name': table_name,
    'type': 'schema',
    'database_id': db_id,  # <-- The actual field name
    'category': f"{table_name}_schema"
}
```

But the original `_wipe_rag_schema()` method was looking for `db_id` instead, causing the wipe to fail silently.

### The Solution
Updated `_wipe_rag_schema()` to check for both field names:
- `database_id` (current, correct field name)
- `db_id` (legacy support for backwards compatibility)

This ensures the wipe works correctly regardless of which field name is present.

## What Gets Cleared

When switching databases, the following are removed from the RAG vector database:

### 1. **Schemas**
- Table definitions
- Column information
- Column types
- Sample values

### 2. **Business Rules**
- Relationship rules (foreign key information)
- Sample data rules (example values per column)

### 3. **Database Settings**
- The old database setting is marked as `is_active=False`

## What Remains

The following are preserved:

- **Conversation History**: All past conversations and messages are maintained in the app database
- **LLM Settings**: Model configuration (Gemini Pro, etc.) is preserved
- **Other Settings**: API keys, system settings, etc.

## User Experience

### From Frontend

When a user switches databases in the Database Settings:

1. Select the new database from the list
2. Toggle `is_active` checkbox to ON
3. Click Save

The system automatically:
- Clears old database RAG data
- Deactivates the previous database
- Extracts and populates RAG with new database schema
- Updates the environment configuration

### From API

```bash
POST /api/settings/database
{
  "name": "New Database",
  "db_type": "postgresql",
  "host": "localhost",
  "port": 5432,
  "database": "new_db",
  "username": "user",
  "password": "pass",
  "is_active": true
}
```

Response will show:
- Old database deactivated
- RAG entries wiped
- New database activated
- New schema extracted

## Testing

### Run the Wipe Logic Test
```bash
python test_rag_wipe_logic.py
```

This test verifies:
- Schemas linked to a database are deleted
- Rules linked to a database are deleted
- Schemas from other databases are preserved
- Rules from other databases are preserved

## Benefits

1. **Data Integrity**: No mixing of data from multiple databases in the vector store
2. **Consistency**: RAG context always matches the currently connected database
3. **Performance**: Only relevant schemas and rules are stored
4. **Security**: Old database information is completely removed when switching

## Troubleshooting

### If RAG Data Isn't Clearing

Check the logs for messages like:
```
Wiping RAG entries for database: [database-id]
[OK] Wiped RAG entries for database: [database-id] (Schemas: X, Rules: Y)
```

If the counts are 0, it means:
- No schemas/rules were found with that database ID
- The database may not have been properly extracted
- Frontend extraction might have failed

### Verify Clearing

Check the RAG database files:
```bash
instance/rag_db/schemas.json
instance/rag_db/rules.json
```

Each entry should have a `metadata` field with `database_id` field pointing to the database ID.

## Files Modified

1. **backend/services/settings_service.py**
   - Enhanced `update_database_settings()` method
   - Fixed `_wipe_rag_schema()` method with correct metadata field name

2. **Test files created**
   - `test_rag_wipe_logic.py` - Direct logic test
   - `test_rag_database_switching.py` - Full integration test (requires app initialization)
