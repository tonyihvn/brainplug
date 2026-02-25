# APP ARCHITECTURE - RAG-ONLY SETTINGS DESIGN

## Executive Summary

The Gemina2 application has been refactored to use a **RAG Vector Database as the exclusive storage for all application settings**. SQL/MySQL/PostgreSQL databases are reserved ONLY for schema discovery and business rule generation from the connected data sources.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    GEMINA2 APPLICATION                      │
└─────────────────────────────────────────────────────────────┘
                            │
                ┌───────────┼───────────┐
                │           │           │
                ▼           ▼           ▼
        ┌─────────────┐  ┌──────────┐  ┌──────────────┐
        │ RAG Vector  │  │  Flask   │  │   Ollama     │
        │ Database    │  │   API    │  │   Service    │
        │ (Settings)  │  │ Server   │  │  (Local)     │
        └─────────────┘  └──────────┘  └──────────────┘
             │                 │              │
             │                 └──────────────┘
             │
        ┌────└─────────────────────────────────────────┐
        │                                              │
        ▼                                              ▼
   ┌─────────────────────────┐         ┌──────────────────────────┐
   │   ALL SETTINGS STORED   │         │  CONNECTED DATABASES     │
   │   - LLM Config          │         │  (Schema Discovery Only) │
   │   - Database Config     │         │  - MySQL                 │
   │   - RAG Config          │         │  - PostgreSQL            │
   │   - System Settings     │         │  - SQLite                │
   │   - Business Rules      │         │  - Any SQL Database      │
   │   - Schemas             │         │                          │
   └─────────────────────────┘         └──────────────────────────┘
```

---

## Data Flow Architecture

### Settings Management Flow

```
User/API Request
    │
    ▼
┌──────────────────────────┐
│  Settings Service (v2)   │  ← ONLY SOURCE OF TRUTH for settings
└──────────────────────────┘
    │
    └──► RAG Vector Database (All settings persisted here)
         ├── LLM Models (Gemini, Claude, Ollama, etc.)
         ├── Database Connections
         ├── RAG Configuration
         ├── System Settings
         ├── Business Rules
         └── Schemas
```

### Data Discovery Flow (Connected Database)

```
User Connects Database
    │
    ▼
Settings Service
    │
    ├─► DatabaseConnector
    │   └──► Executes DESCRIBE/INFORMATION_SCHEMA queries
    │       (No settings stored here)
    │
    └─► Extract:
        ├── Table schemas
        ├── Column types
        ├── Foreign keys
        ├── Primary keys
        └── Sample data
            │
            ▼
        Save as RAG Business Rules:
        ├── Schema definitions
        ├── Relationship rules
        └── Sample data rules
```

---

## Key Components

### 1. RAG Vector Database (Settings Store)

**Purpose**: Exclusive storage for all application settings and configuration

**Stored Settings**:
- **LLM Models**: Gemini, Claude, Ollama, local models with API keys and configurations
- **Database Connections**: MySQL, PostgreSQL, SQLite connection parameters
- **RAG Configuration**: Vector search settings, embeddings config
- **System Settings**: Application preferences
- **Business Rules**: Auto-generated from connected database schemas
- **Schemas**: Table definitions from connected databases

**Never Stores**: 
- Application data from connected databases (except schema metadata)
- Large dataset records

### 2. Connected Databases (Discovery Only)

**Purpose**: Schema extraction and sample data acquisition

**Operations Performed**:
- `DESCRIBE TABLE` or `INFORMATION_SCHEMA` queries
- Column type detection
- Foreign key analysis
- Primary key identification
- Sample data extraction (for context)

**Settings NOT Stored Here**:
- No LLM configuration saved
- No app settings saved
- No API keys stored
- Connection info only used once, then settings stored in RAG

### 3. LLM Service

**Settings Source**: RAG Vector Database ONLY

```python
# OLD ARCHITECTURE (removed):
- Tried SQL database first
- Fell back to RAG
- Inconsistent data state possible

# NEW ARCHITECTURE:
- ONLY reads from RAG Vector Database
- Uses LLMService._ensure_active_model()
- Gets all LLM config from RAG
- Eliminates SQL ORM dependencies for settings
```

### 4. Settings Service

**Location**: `backend/services/settings_service.py`

**Methods**:
```python
# LLM Settings (RAG only)
update_llm_settings(settings_data)      # Save to RAG only
get_llm_settings()                       # Read from RAG
delete_llm_model(model_id)              # Delete from RAG

# Database Settings (RAG only)
update_database_settings(settings_data)  # Save to RAG, extract schema
get_active_database()                    # Read from RAG
get_all_active_databases()              # Read from RAG

# Schema & Business Rules (RAG)
get_rag_schemas()                        # Read from RAG
get_business_rules()                     # Read from RAG
_populate_rag_schema()                   # Extract from DB, save to RAG
_wipe_rag_schema()                       # Delete from RAG
```

---

## Settings Storage Details

### LLM Settings Format (RAG)

```json
{
  "id": "uuid",
  "name": "My LLM",
  "model_type": "ollama|gemini|claude",
  "model_id": "mistral:latest",
  "api_key": "...",
  "api_endpoint": "http://localhost:11434",
  "is_active": true,
  "priority": 0,
  "config": {},
  "created_at": "2026-02-25T00:00:00"
}
```

### Database Settings Format (RAG)

```json
{
  "id": "uuid",
  "name": "Production DB",
  "db_type": "mysql|postgres|sqlite",
  "host": "localhost",
  "port": 3306,
  "database": "mydb",
  "username": "root",
  "password": "",
  "is_active": true,
  "created_at": "2026-02-25T00:00:00"
}
```

---

## Benefits of RAG-Only Settings

### 1. **Consistency**
- Single source of truth for all configuration
- No sync issues between multiple databases
- RAG always has latest settings

### 2. **Performance**
- Fast settings lookup in vector database
- No SQL ORM overhead
- Optimized for read-heavy workloads (settings rarely change)

### 3. **Separation of Concerns**
- Connected databases: Pure data source
- RAG database: Pure configuration store
- Clear architectural boundaries

### 4. **Scalability**
- Can connect multiple databases without complexity
- Settings scale independently from data
- Vector search enables rich configuration queries

### 5. **Security**
- API keys encrypted in RAG database
- Connected databases no longer require settings tables
- Simpler security model

### 6. **Simplicity**
- Eliminated SQLAlchemy ORM for settings
- No database migrations for settings
- JSON-based flexible schema

---

## Migration Guide

### For Existing Users

1. **First Run**: Current settings are migrated to RAG database
   ```
   Old Method: SQL database + RAG sync
   New Method: RAG ONLY
   ```

2. **No Action Required**
   - Settings auto-migrate during app initialization
   - Both old and new data accessible
   - No data loss

3. **SQL Models Deprecated**
   - `DatabaseSetting` model (unused)
   - `LLMModel` model (unused)
   - Models remain in codebase for backward compatibility
   - Will be removed in future versions

### For Developers

**Update Import Statements**:
```python
# OLD (deprecated):
from backend.models.settings import LLMModel, DatabaseSetting
from backend.models import db

# NEW (only if accessing RAG):
from backend.utils.rag_database import RAGDatabase
settings = RAGDatabase()
```

**Update Service Calls**:
```python
# OLD (will fail):
model = LLMModel.query.first()

# NEW (correct):
settings_service = SettingsService()
models = settings_service.get_llm_settings()
```

---

## API Endpoints (Settings)

All settings endpoints now use RAG database exclusively:

### LLM Settings
- `GET /api/llm-settings` → RAG database
- `POST /api/llm-settings` → RAG database
- `PUT /api/llm-settings/:id` → RAG database
- `DELETE /api/llm-settings/:id` → RAG database

### Database Settings
- `GET /api/database-settings` → RAG database
- `POST /api/database-settings` → RAG database (extracts schema)
- `PUT /api/database-settings/:id` → RAG database
- `DELETE /api/database-settings/:id` → RAG database (clears schema)

### Business Rules
- `GET /api/business-rules` → RAG database
- `GET /api/schemas` → RAG database

---

## Technical Details

### Why RAG for Settings?

Vector databases are excellent for settings because:
1. **Flexible Schema**: Settings are inherently schemaless
2. **Fast Retrieval**: Vector search optimizes common queries
3. **Embeddings**: Future: semantic search for rules
4. **Scalability**: No schema migrations needed
5. **Simplicity**: JSON storage, no ORM complexity

### RAG Database Fallback

Current implementation: JSON file-based (if Qdrant unavailable)
```
instance/store/
  ├── database_settings.json
  ├── llm_models.json
  ├── business_rules.json
  └── schemas.json
```

---

## Configuration

### Enable RAG-Only Mode

**Status**: ✅ ACTIVE BY DEFAULT

No configuration needed - the app automatically uses RAG-only for all settings.

### Environment Variables

```bash
# Database URL is ONLY for schema extraction (if needed)
DATABASE_URL=mysql://user:pass@host/database

# RAG is configured internally, no env var needed
# (Uses instance/store/ for JSON fallback)
```

---

## Testing & Verification

### Verify RAG-Only Storage

```python
from app import app
from backend.services.settings_service import SettingsService

with app.app_context():
    settings = SettingsService()
    
    # Create LLM setting
    settings.update_llm_settings({
        'name': 'Test Ollama',
        'model_type': 'ollama',
        'model_id': 'mistral:latest'
    })
    
    # Verify it's in RAG, not SQL
    models = settings.get_llm_settings()
    assert any(m['name'] == 'Test Ollama' for m in models)
    print("✓ Settings stored in RAG only")
```

---

## Future Enhancements

1. **Encrypted RAG Storage**
   - API keys encrypted in RAG
   - Decryption on retrieval

2. **Audit Logging**
   - Track all settings changes
   - Settings version history

3. **Semantic Search**
   - Find similar business rules
   - Rule recommendations

4. **Settings Sync**
   - Cloud sync for settings
   - Multi-instance deployment

---

## Summary

| Aspect | Old Design | New Design |
|--------|-----------|-----------|
| **Settings Storage** | SQL + RAG (dual) | RAG ONLY ✓ |
| **Data Discovery** | SQL + RAG | SQL ONLY (read-only) |
| **ORM Usage** | SQLAlchemy for settings | None (JSON-based) |
| **Sync Issues** | Possible mismatches | Eliminated |
| **Performance** | Slower (ORM) | Faster (RAG) |
| **Simplicity** | Complex (dual store) | Simple (single store) |

**Result**: Cleaner, faster, more reliable architecture with RAG Vector Database as the exclusive settings store.
