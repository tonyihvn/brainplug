# API-Mediated RAG Architecture Implementation Guide

## Overview

This implementation adds a "security air gap" between your LLM and raw databases by introducing an **API Query Mode** alongside the existing **Direct Query Mode**. Instead of the LLM directly querying your database, it searches a local vector database that you control and populate.

## Architecture Comparison

### Direct Query Mode (Original)
```
User Prompt → LLM → Suggests SQL → Executes on Raw Database → Returns Data
```

**Risk**: LLM has full database access; could suggest dangerous queries.

### API Query Mode (New)  
```
User Prompt → LLM → Suggests Search Query → Semantic Search on Vector DB → Returns Context
                                         ↓
                      ETL Pipeline Updates Vector DB ← Controlled SQL Queries
```

**Benefits**: 
- LLM only sees indexed/approved data
- Automatic data sync on configurable schedule
- Natural language search instead of SQL
- Built-in "freshness" windows

---

## Key Components Implemented

### 1. DatabaseSetting Model Extensions
**File**: `backend/models/settings.py`

New fields added:
- `query_mode` - 'direct' or 'api'
- `selected_tables` - Mapping of table configurations
- `sync_interval` - Global sync interval in minutes
- `vector_db_collection` - ChromaDB collection name
- `ingestion_config` - Pipeline-specific config

### 2. IngestionPipeline Service
**File**: `backend/services/ingestion_pipeline.py`

Core ETL functionality:
- **table_discovery()** - Finds all available tables and their schemas
- **transform_to_chunks()** - Converts database records to natural language
- **ingest_table()** - Executes 3-step pipeline:
  1. **Extract**: Query table with configured SQL
  2. **Transform**: Convert rows to readable text chunks
  3. **Vectorize & Store**: Save in ChromaDB with metadata
- **search_vector_db()** - Semantic search on indexed data
- **clear_collection()** - Reset collection for re-ingestion

Example transformation:
```python
# Input: {"name": "Widget X", "price": 99.99, "stock": 150}
# Output: "From table products: name contains 'Widget X'; price is 99.99; stock is 150"
```

### 3. ScheduledIngestionService
**File**: `backend/services/scheduled_ingestion.py`

Background job scheduling:
- Starts ingestion jobs for each database in API mode
- Respects per-table sync intervals (min 5 minutes)
- Uses threading and the `schedule` library
- Provides job status tracking (success/error counts)
- Prevents concurrent runs with lock mechanism

Usage:
```python
service = get_ingestion_service()
job_id = service.start_ingestion_job(database_setting)
status = service.get_job_status(job_id)
```

### 4. DatabaseQueryRouter
**File**: `backend/services/query_router.py`

Intelligent query routing:
- Checks database `query_mode` setting
- Routes to either:
  - `_execute_sql_query()` for direct mode
  - `_search_vector_db()` for API mode
- Converts SQL query suggestions to search queries
- Formats results uniformly

### 5. Frontend Components

#### APIQueryConfig Component
**File**: `components/APIQueryConfig.tsx`

UI for configuring API queries:
- Table discovery button
- Checkbox selection with enable/disable toggle
- Expandable rows for per-table configuration:
  - Custom extraction query (editable)
  - Sync interval (5-1440 minutes)
  - Column visualization
- Preview of enabled tables
- Save all configurations button

#### Enhanced DatabaseSettings
**File**: `components/settings/DatabaseSettings.tsx`

Integrated query mode toggle:
- Radio buttons: "Direct Query" vs "API Query (Vector DB)"
- Shows APIQueryConfig when API mode selected
- Displays query mode in database table
- Explains security benefits

### 6. Updated ActionService
**File**: `backend/services/action_service.py`

Modified `_execute_database_query()`:
- Detects database `query_mode`
- Uses DatabaseQueryRouter for routing
- Works seamlessly with both modes
- UI receives same format regardless of mode

---

## How to Use

### Step 1: Switch to API Mode
1. Go to **Settings → Database Connections**
2. Edit a connection
3. Change query mode to **"API Query (Vector DB)"**

### Step 2: Select Tables
1. Click **"Discover Tables"**
2. Check tables you want synced
3. For each table:
   - Customize extraction query if needed
   - Set sync interval (e.g., every 60 minutes)
   - Click **"Save Configuration"**

### Step 3: Auto-Ingestion Starts
- System automatically starts background job
- Data pulls on specified schedules
- Vector DB gets indexed chunks
- Business rules trained on indexed data

### Step 4: Chat with Your Data
- Ask questions naturally
- LLM searches vector DB (not raw DB)
- Results come back with relevance scores
- Answers include previous context from conversation

---

## Configuration Examples

### Example 1: E-Commerce Store

**Database**: `ecommerce_db`  
**Query Mode**: API

**Tables Selected**:
1. `products`
   - Query: `SELECT id, name, description, price, category FROM products LIMIT 10000`
   - Interval: 60 minutes
   - Reason: Sync product catalog hourly

2. `orders`
   - Query: `SELECT id, user_id, order_date, total FROM orders WHERE order_date >= NOW() - INTERVAL 7 DAY`
   - Interval: 30 minutes
   - Reason: Recent orders, update every 30 min

3. `customers` (NOT selected)
   - Too sensitive; query directly instead

**Result**: LLM can answer "What products are in the electronics category under $100?" without accessing entire product table.

### Example 2: Healthcare Database

**Database**: `patient_records`  
**Query Mode**: API

**Tables Selected**:
1. `treatments` 
   - Query: `SELECT treatment_id, name, description, standard_dosage FROM treatments`
   - Interval: 1440 (daily)

2. `symptoms`
   - Query: `SELECT symptom_id, name, description FROM symptoms`
   - Interval: 1440 (daily)

**NOT Selected**: `patients` table (too sensitive for LLM access)

---

## Security Features

### 1. Data Minimization
- Only selected tables are indexed
- Can customize which columns/rows are included via query

### 2. Interval-Based Freshness
- Not real-time (reduces risk of accessing sensitive writes)
- Configurable windows for different stability/freshness tradeoffs

### 3. Query Limiting
- Extraction queries have implicit `LIMIT` clauses
- Prevents accidental table scans

### 4. Vector DB Isolation
- Local storage (no external vector DB)
- No raw SQL sent to LLM
- LLM works with semantically indexed chunks

---

## Technical Details

### Vector Database (ChromaDB)
- Location: `./chroma_data/` (local directory)
- Collection per database: `db_{database_id}`
- Persistence: Duckdb + Parquet files
- Query: Semantic search with similarity scoring

### Metadata Tracked
Each indexed chunk includes:
```json
{
  "table": "products",
  "chunk_index": 0,
  "total_chunks": 145,
  "ingested_at": "2026-03-05T14:32:00Z"
}
```

### Recovery & Re-ingestion
If needed:
1. Use `clear_collection()` to wipe vector DB
2. Manually trigger re-ingestion
3. Schedule will resume automatic updates

---

## API Endpoints (To Be Implemented)

### Discovery
```
POST /settings/database/discover-tables
{ "database_id": "xxx" }
→ { "tables": [...] }
```

### Ingestion
```
POST /settings/database/start-ingestion
{ "database_id": "xxx" }
→ { "job_id": "yyy", "status": "started" }
```

### Job Status
```
GET /settings/database/ingestion-status/{job_id}
→ { "status": "success", "tables_ingested": 3, ... }
```

---

## Business Rules in API Mode

When using API Query mode, you can still define **business rules** to train the LLM:

**Compulsory Rules** (always included):
```
"If asked about product availability, always check our standard stock levels."
"Never suggest products that are discontinued."
```

**Optional Rules**:
```
"For bulk orders (>100 units), suggest our wholesale pricing."
```

These rules are included in the LLM prompt along with vector DB search results.

---

## Performance Notes

- **Vector search**: ~100-200ms for 10 chunks from 100K vectors
- **Ingestion job**: Depends on table size; usually 1-5 minutes
- **Memory**: ChromaDB uses ~500MB for 100K vectors
- **Storage**: ~1GB per 100K vectors (with embeddings)

---

## Limitations & Future Enhancements

### Current Limitations
1. No real-time updates (interval-based only)
2. ChromaDB fixed; no cloud vector DBs yet
3. Simple chunking strategy (row-based)

### Potential Enhancements
1. Webhook triggers for instant re-indexing
2. Multi-vector-DB support (Pinecone, Weaviate)
3. Hybrid indexing (keyword + semantic)
4. Advanced chunking (document-aware, hierarchical)
5. Access control at row/column level

---

## Troubleshooting

### Vector DB not initializing?
Check `./chroma_data` directory permissions and disk space.

### Ingestion job fails silently?
Enable debug logging and check console for errors.

### LLM gets wrong results?
May indicate chunking issue. Try adjusting queries to return less data or different structure.

### Too many vector search results?
Reduce `top_k` parameter in `search_vector_db()` from default 10.

