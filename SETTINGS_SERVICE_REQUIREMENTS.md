# SettingsService Complete Requirements

## Overview

**Purpose**: Central service for managing database connections, LLM models, RAG data, and system settings. Acts as a bridge between Flask API endpoints and persistent storage (JSON Store + RAGDatabase).

**Location**: `backend/services/settings_service.py`

**Key Dependencies**:
- `backend.utils.rag_database.RAGDatabase` - Vector/semantic storage for schemas and rules
- `backend.utils.json_store.JSONStore` - Persistent JSON storage for settings
- `backend.utils.database.DatabaseConnector` - Schema extraction and DB introspection
- `backend.models.settings.DatabaseSetting` - SQLAlchemy model for database settings
- `backend.models.settings.LLMModel` - SQLAlchemy model for LLM configurations

---

## Public Methods (API Contract)

### 1. Database Settings Management

#### `get_database_settings() -> List[Dict]`
- **Returns**: All database connection settings (from JSONStore)
- **Structure**: `[{"id": "uuid", "name": "...", "db_type": "mysql|sqlite|postgres", "host": "...", "port": 3306, "database": "...", "username": "...", "password": "...", "is_active": True|False, "created_at": "ISO8601", "updated_at": "ISO8601"}, ...]`
- **Used by**: GET `/api/settings/database`
- **Called in**: `test_rag_persistence.py`, `comprehensive_rag_test.py`, `trigger_rag.py`, `test_populate_debug.py`

#### `get_active_database() -> Optional[Dict]`
- **Returns**: The currently active database setting (where `is_active=True`)
- **Structure**: Single database setting dict (same as above)
- **Returns None** if no database is active
- **Used by**: RAG population, database schema extraction logic
- **Called in**: `analyze_database_schema.py`, `test_relationship_creation.py`, `test_populate_debug.py`, `trigger_rag.py`

#### `update_database_settings(settings_data: Dict) -> Dict`
- **Input**: Database setting dict with required fields
- **Behavior**:
  1. Validate/parse connection string
  2. Test database connection (does not fail app if connection fails)
  3. If `is_active=True`, deactivate all other database settings
  4. Save to JSONStore (persists in `instance/store/database_settings.json`)
  5. If **activating** a NEW database (switching from one to another):
     - Test connection to new database
     - Automatically trigger `_populate_rag_schema(new_db)` to extract schema
     - Wipe old RAG data for previous database (if any)
  6. If **updating** active database (same db, different settings):
     - Just update the settings, don't repopulate RAG
- **Returns**: Updated/created database setting dict with ID
- **Used by**: POST `/api/settings/database`
- **Called in**: `scripts/test_db_full_flow.py`, `scripts/test_rag_integration.py`

#### `delete_database_setting(setting_id: str) -> bool`
- **Behavior**:
  1. Delete from JSONStore
  2. Delete associated RAG schemas (via `_wipe_rag_schema()`)
  3. Delete associated RAG rules
  4. If was active, select next available database as active
- **Returns**: `True` if deleted, `False` if not found
- **Used by**: DELETE `/api/settings/database/<setting_id>`

#### `_build_connection_string(db_setting: Dict) -> str`
- **Purpose**: Build SQLAlchemy connection string from database setting
- **Support**: mysql+pymysql, sqlite, postgres, etc.
- **Example**: 
  - MySQL: `mysql+pymysql://user:pass@host:3306/database`
  - SQLite: `sqlite:////absolute/path/to/file.db`
  - PostgreSQL: `postgresql://user:pass@host:5432/database`
- **Called by**: DatabaseConnector, schema extraction logic

---

### 2. RAG Schema & Rule Management

#### `get_rag_schemas() -> List[Dict]`
- **Returns**: All schemas from RAGDatabase, formatted for frontend display
- **Structure**: `[{"id": "unique_id", "title": "table_name", "content": "...", "metadata": {...}, "database_id": "..."}, ...]`
- **Data source**: Reads from `instance/rag_db/schemas.json` via RAGDatabase
- **Used by**: GET `/api/rag/schema`, GET `/api/settings/rag` partially
- **Called in**: `test_rag_persistence.py`, `comprehensive_rag_test.py`

#### `get_business_rules() -> List[Dict]`
- **Returns**: All business rules from RAGDatabase (relationships, sample data, custom rules)
- **Structure**: 
  ```python
  [{
    "id": "unique_id",
    "content": "rule_content",
    "metadata": {
      "type": "relationship|sample_data|rule",
      "name": "friendly_name",
      "database_id": "...",
      "table_name": "...",
      "category": "...",
      "is_active": True
    }
  }, ...]
  ```
- **Data source**: Reads from `instance/rag_db/rules.json` via RAGDatabase
- **Used by**: RAG retrieval for LLM context
- **Called in**: `test_rag_persistence.py`, `comprehensive_rag_test.py`

#### `_populate_rag_schema(db_setting: Dict) -> None`
- **Purpose**: Extract database schema and populate RAG with tables, foreign keys, and sample data
- **Input**: Single database setting dict (with `id`, `name`, connection details)
- **Behavior**:
  1. Get database schema via DatabaseConnector.get_schema()
  2. For each table:
     - Create **schema entry**: `add_schema(table_name, schema_content, db_id)`
       - Includes column names, types, nullable, primary keys, foreign keys, sample values
       - Stored with metadata: `{table_name, database_id, type: "schema"}`
     - Create **sample data rule** if table has rows: `add_business_rule(..., meta_type='sample_data')`
       - Shows typical data values
  3. For each table with foreign keys:
     - Create **relationship rule**: `add_business_rule(..., meta_type='relationship')`
       - Lists all FK relationships: "col1, col2 -> referenced_table(ref_col1, ref_col2)"
       - **CRITICAL FIX**: Rule ID must include `meta_type` suffix to distinguish relationship from sample_data
       - Format: `f"{db_id}_{table_name}_relationship_rule"` not just `f"{db_id}_{table_name}_rule"`
  4. Save all to RAGDatabase (ChromaDB/Qdrant with JSON fallback)
- **Error handling**: Catch and log errors, don't fail app
- **Called by**: `update_database_settings()` when activating new database, manual script `trigger_rag.py`
- **Called in**: `test_populate_debug.py`, `trigger_rag.py`, `test_relationship_creation.py`

#### `_wipe_rag_schema(db_id: str) -> None`
- **Purpose**: Delete all RAG schemas and rules for a specific database
- **Behavior**:
  1. Delete all schemas where `metadata.database_id == db_id`
  2. Delete all rules where `metadata.database_id == db_id`
  3. Pure cleanup, no side effects
- **Called by**: `delete_database_setting()`, `update_database_settings()` when switching databases
- **Called in**: `test_populate_debug.py`

---

### 3. LLM Settings Management

#### `get_llm_settings() -> List[Dict]`
- **Returns**: All LLM models from RAGDatabase (fallback to SQLAlchemy if RAG unavailable)
- **Structure**: 
  ```python
  [{
    "id": "uuid",
    "name": "Model Name",
    "model_type": "ollama|openai|claude|mistral|other",
    "model_id": "mistral:7b",
    "api_key": "...",
    "api_endpoint": "...",
    "priority": 0,  # Lower = higher priority
    "is_active": True|False,
    "config": {}
  }, ...]
  ```
- **Fallback strategy**: If RAG read fails, read from LLMModel SQLAlchemy table
- **Used by**: GET `/api/settings/llm`
- **Called in**: `app.py` endpoint handler

#### `update_llm_settings(settings_data: Dict) -> Dict`
- **Behavior**:
  1. Create or update LLM model in RAGDatabase.save_setting()
  2. Also save to SQLAlchemy LLMModel table (backup)
  3. If `is_active=True`, deactivate other models
  4. Trigger refresh of global `llm_service` to pick up changes immediately
- **Returns**: Updated/created LLM settings dict
- **Used by**: POST `/api/settings/llm`

#### `delete_llm_model(model_id: str) -> bool`
- **Behavior**: Delete from RAGDatabase and SQLAlchemy
- **Returns**: `True` if deleted, `False` if not found
- **Used by**: DELETE `/api/settings/llm/<model_id>`

#### `list_local_ollama_models(host: str = 'http://localhost:11434') -> Dict`
- **Purpose**: Probe local Ollama daemon for available models
- **Returns**: `{"models": ["mistral:7b", "llama2", ...], "host": "...", "errors": [...]}`
- **Used by**: GET `/api/settings/llm/ollama/models`
- **Graceful failure**: Returns empty models list if Ollama not reachable

---

### 4. Other Settings

#### `get_rag_settings() -> Dict`
- **Returns**: RAG configuration (if applicable)
- **Example**: `{"enabled": True, "model": "all-MiniLM-L6-v2", ...}`

#### `update_rag_settings(settings_data: Dict) -> Dict`
- **Behavior**: Update RAG configuration settings
- **Returns**: Updated settings dict

#### `get_system_settings() -> Dict`
- **Returns**: System-level settings (SMTP, IMAP, POP, etc.)

#### `update_system_settings(settings_data: Dict) -> Dict`
- **Updates system configuration**

#### `get_api_configs() -> List[Dict]`
- **Returns**: All API configurations

#### `create_api_config(config_data: Dict) -> Dict`
- **Creates new API config**

#### `update_api_config(config_id: str, config_data: Dict) -> Dict`
- **Updates API config**

#### `delete_api_config(config_id: str) -> bool`
- **Deletes API config**

---

## Data Structures

### Database Setting Object
```python
{
    "id": "550e8400-e29b-41d4-a716-446655440000",  # UUID
    "name": "Production MySQL",
    "db_type": "mysql",  # One of: mysql, sqlite, postgres, mssql
    "host": "localhost",
    "port": 3306,
    "database": "iventory",
    "username": "root",
    "password": "secret",
    "is_active": True,  # Only one database can be active
    "created_at": "2025-02-24T10:30:00.000000",
    "updated_at": "2025-02-24T10:30:00.000000"
}
```

### RAG Schema Object (from RAGDatabase)
```python
{
    "id": "db_id_table_name_schema",
    "content": "Table information with columns, types, constraints...",
    "metadata": {
        "table_name": "users",
        "type": "schema",
        "database_id": "550e8400-e29b-41d4-a716-446655440000",
        "category": "users_schema"
    },
    "embedding": [0.1, 0.2, ...]  # Optional semantic embedding
}
```

### Business Rule Object (from RAGDatabase)
```python
{
    "id": "db_id_table_name_relationship_rule",  # CRITICAL: includes type suffix!
    "content": "Relationship description or rule content",
    "metadata": {
        "type": "relationship|sample_data|rule",  # CRITICAL for filtering
        "name": "users_relationships",
        "rule_name": "users_relationships",
        "rule_type": "optional|compulsory",
        "database_id": "550e8400-e29b-41d4-a716-446655440000",
        "category": "users",
        "is_active": True
    },
    "embedding": [0.1, 0.2, ...]  # Optional semantic embedding
}
```

### LLM Model Object
```python
{
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "name": "Local Mistral",
    "model_type": "ollama",  # One of: ollama, openai, claude, mistral
    "model_id": "mistral:7b",
    "api_key": None,  # For local Ollama
    "api_endpoint": "http://localhost:11434",
    "priority": 0,  # Lower = higher priority
    "is_active": True,
    "config": {},
    "created_at": "2025-02-24T10:30:00.000000"
}
```

---

## RAGDatabase Integration

### Methods SettingsService Uses

#### Schema Management
- **`add_schema(table_name: str, schema_content: str, db_id: str) -> bool`**
  - Adds table schema to RAGDatabase
  - Stores in ChromaDB/Qdrant with JSON fallback
  - Returns True if successful

#### Rule Management
- **`add_business_rule(rule_name: str, rule_content: str, db_id: str, rule_type: str = "optional", category: str = None, meta_type: str = None) -> bool`**
  - Adds business rule (relationship, sample data, or custom)
  - **CRITICAL**: `meta_type` parameter distinguishes rule type (must be passed!)
  - Example: `add_business_rule("users_relationships", rel_content, db_id, meta_type="relationship")`
  - Returns True if successful

#### Data Retrieval
- **`get_all_schemas() -> List[Dict]`**
  - Returns all schemas from JSON backup (since Qdrant doesn't have simple list API)
  
- **`get_all_rules() -> List[Dict]`**
  - Returns all rules from JSON backup

#### Deletion
- **`delete_schema(table_name: str) -> bool`**
  - Delete schema by table name
  
- **`delete_rule(rule_id: str) -> bool`**
  - Delete rule by rule ID

#### Querying
- **`query_schemas(query: str, n_results: int = 5) -> List[Dict]`**
  - Semantic search for schemas
  
- **`query_rules(query: str, n_results: int = 10) -> List[Dict]`**
  - Semantic search for rules

#### Settings Persistence
- **`save_setting(setting_id: str, setting: Dict) -> Dict`**
  - Generic save for settings (LLM models, etc.)
  - Uses ChromaDB/Qdrant or JSON fallback

---

## Special Logic Requirements

### 1. Database Activation Flow
```
POST /api/settings/database with is_active=True
  ↓
update_database_settings()
  ↓
  1. Save to JSONStore
  2. Deactivate old active database
  3. Test new database connection
  4. IF connection successful:
     - _populate_rag_schema(new_db)  <- Auto-populate RAG
     - _wipe_rag_schema(old_db_id)   <- Clean old data
  5. Return updated setting
  ↓
RAG is now populated with new database structure
```

### 2. RAG Population Logic (Critical)
When `_populate_rag_schema()` is called:

```python
for each table in database:
    # 1. Create schema entry
    schema_content = "Columns:\n- col1 (type1)\n..."
    rag_db.add_schema(table_name, schema_content, db_id)
    
    # 2. Create sample data rule (if data exists)
    sample_content = "Sample data from table: row1, row2, ..."
    rag_db.add_business_rule(
        rule_name=f"{db_name}_{table_name}_sample_data",
        rule_content=sample_content,
        db_id=db_id,
        category=f"{db_id}_{table_name}",
        meta_type="sample_data"  # CRITICAL!
    )
    
    # 3. Create relationship rule (if FK exists)
    if table.foreign_keys:
        rel_content = "Relationships:\n- col1 -> ref_table(ref_col)"
        rag_db.add_business_rule(
            rule_name=f"{db_name}_{table_name}_relationships",
            rule_content=rel_content,
            db_id=db_id,
            category=f"{db_id}_{table_name}",
            meta_type="relationship"  # CRITICAL! Distinguishes from sample_data
        )
```

**Why meta_type matters**: Without it, adding both sample_data and relationship for the same table would overwrite the first rule with the second (same ID). With meta_type:
- Sample data rule ID: `db_id_table_name_sample_data_rule`
- Relationship rule ID: `db_id_table_name_relationship_rule`

### 3. Connection String Building
Support these formats:
- **MySQL**: `mysql+pymysql://user:password@host:port/database`
- **SQLite**: `sqlite:///path/to/file.db`
- **PostgreSQL**: `postgresql://user:password@host:port/database`
- **MSSQL**: `mssql+pyodbc://user:password@host/database?driver=ODBC+Driver+17+for+SQL+Server`

Handle edge cases:
- SQLite paths may be relative or absolute
- PostgreSQL default port is 5432
- MySQL default port is 3306
- Empty credentials for some SQLite setups

---

## Error Handling Strategy

1. **Connection failures**: Log but don't crash app
   ```python
   try:
       if not db_connector.test_connection(conn_str):
           logger.warning(f"Connection failed: {conn_str}")
           # Still save the setting, user may fix credentials later
   except Exception as e:
       logger.error(f"Connection test error: {e}")
   ```

2. **RAG failures**: Graceful degradation
   ```python
   try:
       rag_db.add_schema(...)
   except Exception as e:
       logger.error(f"Failed to add schema to RAG: {e}")
       # But continue processing other tables
   ```

3. **Missing optional data**: No failure
   ```python
   schemas = rag_db.get_all_schemas()
   if not schemas:
       logger.warning("No schemas in RAG")
       return []  # Return empty list, not error
   ```

---

## Constructor & Initialization

```python
class SettingsService:
    def __init__(self):
        """Initialize SettingsService with dependencies."""
        self.json_store = JSONStore()  # Persistent JSON storage
        self.rag_db = RAGDatabase()    # Vector/semantic storage
        self.db_connector = DatabaseConnector()  # Schema extraction
        # Optional: Load LLM models from database at init
```

---

## Testing Points

### Test Files Reference
- `test_rag_persistence.py` - Full workflow test
- `comprehensive_rag_test.py` - Diagnostic tests
- `test_populate_debug.py` - RAG population debugging
- `test_fix_verification.py` - Relationship rule verification
- `test_relationship_creation.py` - FK relationship handling
- `trigger_rag.py` - Manual RAG population trigger
- `scripts/test_db_full_flow.py` - End-to-end database flow

### Critical Scenarios to Test
1. ✅ Create database, auto-populate RAG
2. ✅ Switch active database, wipe old RAG
3. ✅ Update database password, keep RAG
4. ✅ All relationship rules created with unique IDs
5. ✅ Sample data rules created separately from relationships
6. ✅ Get active database when multiple exist
7. ✅ Handle connection failures gracefully
8. ✅ Restore to SQLAlchemy if RAG unavailable

---

## Summary of All Public Methods

| Method | Returns | Purpose |
|--------|---------|---------|
| `get_database_settings()` | `List[Dict]` | Get all DB connections |
| `get_active_database()` | `Optional[Dict]` | Get active DB only |
| `update_database_settings(data)` | `Dict` | Create/update DB, auto-populate RAG |
| `delete_database_setting(id)` | `bool` | Delete DB, wipe RAG |
| `get_rag_schemas()` | `List[Dict]` | All schemas for LLM |
| `get_business_rules()` | `List[Dict]` | All rules (relationships, samples) |
| `get_llm_settings()` | `List[Dict]` | All LLM models |
| `update_llm_settings(data)` | `Dict` | Create/update LLM |
| `delete_llm_model(id)` | `bool` | Delete LLM |
| `list_local_ollama_models(host)` | `Dict` | Probe Ollama |
| `get_rag_settings()` | `Dict` | RAG configuration |
| `update_rag_settings(data)` | `Dict` | Update RAG config |
| `get_system_settings()` | `Dict` | System config |
| `update_system_settings(data)` | `Dict` | Update system config |
| `get_api_configs()` | `List[Dict]` | All API configs |
| `create_api_config(data)` | `Dict` | Create API config |
| `update_api_config(id, data)` | `Dict` | Update API config |
| `delete_api_config(id)` | `bool` | Delete API config |
| `_populate_rag_schema(db)` | `None` | Extract & populate RAG |
| `_wipe_rag_schema(db_id)` | `None` | Delete all RAG for DB |
| `_build_connection_string(db)` | `str` | Build SQLAlchemy URI |

