# API-Mediated RAG - Quick Start Guide

## What's Been Implemented ✅

You now have a complete **API-Mediated RAG architecture** that creates a security "air gap" between your LLM and raw databases. Here's what's ready:

### Backend Services (Python)
1. **IngestionPipeline** - ETL for pulling data into vector DB
2. **ScheduledIngestionService** - Background jobs for periodic sync
3. **DatabaseQueryRouter** - Routes queries based on database mode
4. **Updated ActionService** - Supports both direct and API modes

### Frontend Components (React/TypeScript)
1. **APIQueryConfig** - Table discovery and configuration UI
2. **BusinessRulesTrainer** - Train LLM with domain rules
3. **Enhanced DatabaseSettings** - Query mode toggle

### Documentation
- `API_MEDIATED_RAG_GUIDE.md` - Full architecture guide
- `IMPLEMENTATION_SUMMARY.md` - Technical implementation details

---

## Next Steps: Backend API Endpoints

Your backend needs 4 new endpoints. Here's the implementation:

### 1. Create Settings Blueprint/Routes File

**File**: `backend/routes/settings_api.py` (or add to existing settings route)

```python
from flask import Blueprint, request, jsonify
from backend.services.ingestion_pipeline import IngestionPipeline
from backend.services.scheduled_ingestion import get_ingestion_service
from backend.services.settings_service import SettingsService
from backend.utils.logger import setup_logger
import uuid

logger = setup_logger(__name__)
settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

# ============================================================================
# API Query Configuration Endpoints
# ============================================================================

@settings_bp.route('/database/discover-tables', methods=['POST'])
def discover_tables():
    """
    Discover all tables in a database for API Query mode setup.
    """
    try:
        data = request.json
        database_id = data.get('database_id')
        
        if not database_id:
            return jsonify({'status': 'error', 'message': 'database_id required'}), 400
        
        # Get database setting
        settings_service = SettingsService()
        db_settings = settings_service.get_database_settings()
        database_setting = next((s for s in db_settings if s.get('id') == database_id), None)
        
        if not database_setting:
            return jsonify({'status': 'error', 'message': 'Database not found'}), 404
        
        # Discover tables
        pipeline = IngestionPipeline()
        tables = pipeline.discover_tables(database_setting)
        
        logger.info(f"✓ Discovered {len(tables)} tables for {database_id}")
        
        return jsonify({
            'status': 'success',
            'data': tables
        }), 200
        
    except Exception as e:
        logger.error(f"Error discovering tables: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@settings_bp.route('/database/start-ingestion', methods=['POST'])
def start_ingestion():
    """
    Start automatic ingestion job for a database in API mode.
    """
    try:
        data = request.json
        database_id = data.get('database_id')
        
        if not database_id:
            return jsonify({'status': 'error', 'message': 'database_id required'}), 400
        
        # Get database setting
        settings_service = SettingsService()
        db_settings = settings_service.get_database_settings()
        database_setting = next((s for s in db_settings if s.get('id') == database_id), None)
        
        if not database_setting:
            return jsonify({'status': 'error', 'message': 'Database not found'}), 404
        
        # Check query mode
        if database_setting.get('query_mode') != 'api':
            return jsonify({
                'status': 'error',
                'message': 'Database is not in API query mode'
            }), 400
        
        # Start ingestion job
        ingestion_service = get_ingestion_service()
        job_id = ingestion_service.start_ingestion_job(database_setting)
        
        logger.info(f"✓ Started ingestion job {job_id} for {database_id}")
        
        return jsonify({
            'status': 'success',
            'data': {
                'job_id': job_id,
                'database_id': database_id,
                'message': f'Ingestion job started. Data will be synced according to table intervals.'
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Error starting ingestion: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@settings_bp.route('/database/ingestion-status/<job_id>', methods=['GET'])
def get_ingestion_status(job_id):
    """
    Get status of an active ingestion job.
    """
    try:
        ingestion_service = get_ingestion_service()
        status = ingestion_service.get_job_status(job_id)
        
        if not status:
            return jsonify({
                'status': 'error',
                'message': f'Job {job_id} not found'
            }), 404
        
        return jsonify({
            'status': 'success',
            'data': status
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@settings_bp.route('/database/all-ingestion-jobs', methods=['GET'])
def get_all_ingestion_jobs():
    """
    Get status of all active ingestion jobs.
    """
    try:
        ingestion_service = get_ingestion_service()
        jobs = ingestion_service.get_all_jobs()
        
        return jsonify({
            'status': 'success',
            'data': jobs
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting jobs: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
```

### 2. Register Blueprint in Your Main App

**In your main Flask app file** (e.g., `app.py`):

```python
from backend.routes.settings_api import settings_bp

# Register blueprints
app.register_blueprint(settings_bp)

# OR if you have an existing settings blueprint:
# Merge the routes into your existing settings route file
```

### 3. Update Database Settings Route (if needed)

When updating a database setting with `query_mode='api'`, call:

```python
@app.route('/settings/database', methods=['POST'])
def save_database_setting():
    # ... existing code to save settings ...
    
    # After saving, if query_mode is 'api', start ingestion
    if data.get('query_mode') == 'api' and data.get('is_active'):
        settings_service = SettingsService()
        database_setting = settings_service.get_database_settings()
        db = next((s for s in database_setting if s.get('id') == data.get('id')), None)
        
        if db and db.get('selected_tables'):
            ingestion_service = get_ingestion_service()
            try:
                job_id = ingestion_service.start_ingestion_job(db)
                response['data']['ingestion_job_id'] = job_id
            except Exception as e:
                logger.warning(f"Could not start ingestion: {str(e)}")
    
    return response
```

---

## Installation & Setup

### 1. Install Required Packages

```bash
pip install chromadb schedule
```

### 2. Create Vector DB Directory

```bash
mkdir -p ./chroma_data
```

### 3. Run Your App

The ScheduledIngestionService will initialize automatically when:
- Your app starts
- A database is set to API mode
- The first ingestion job is registered

---

## Testing the Implementation

### Test 1: Table Discovery

```bash
curl -X POST http://localhost:5000/settings/database/discover-tables \
  -H "Content-Type: application/json" \
  -d '{"database_id": "your-db-id"}'
```

### Test 2: Start Ingestion

```bash
curl -X POST http://localhost:5000/settings/database/start-ingestion \
  -H "Content-Type: application/json" \
  -d '{"database_id": "your-db-id"}'
```

### Test 3: Check Job Status

```bash
curl http://localhost:5000/settings/database/ingestion-status/job-id-here
```

---

## Frontend Usage

### In Your App Component

```typescript
import APIQueryConfig from '@/components/APIQueryConfig'
import BusinessRulesTrainer from '@/components/BusinessRulesTrainer'

export function SettingsPage() {
  return (
    <>
      <DatabaseSettings />
      {/* APIQueryConfig is automatically shown when API mode is selected */}
      
      <BusinessRulesTrainer 
        forDatabaseMode="api"
        onRulesUpdated={() => {
          // Refresh rules if needed
        }}
      />
    </>
  )
}
```

---

## How Users Will Interact

### Step 1: Switch to API Mode
1. Settings → Database Connections
2. Edit a database
3. Choose "API Query (Vector DB)" mode
4. Save

### Step 2: Configure Tables
1. Click "Discover Tables"
2. Check tables to sync
3. Customize queries if needed
4. Set sync intervals
5. Save configuration

### Step 3: Talk to Your Data
1. LLM asks: "What products cost under $100?"
2. System searches vector DB
3. Returns relevant chunks instead of raw table
4. LLM answers based on semantic search results

---

## Key Files Reference

**Backend**:
- `backend/services/ingestion_pipeline.py` - ETL pipeline
- `backend/services/scheduled_ingestion.py` - Background jobs
- `backend/services/query_router.py` - Query routing logic
- `backend/models/settings.py` - Extended database model

**Frontend**:
- `components/APIQueryConfig.tsx` - Table setup UI
- `components/BusinessRulesTrainer.tsx` - Rule management
- `components/settings/DatabaseSettings.tsx` - Query mode toggle

**Docs**:
- `API_MEDIATED_RAG_GUIDE.md` - Full guide
- `IMPLEMENTATION_SUMMARY.md` - Tech details

---

## Architecture Overview

```
User Query
    ↓
LLM Processing
    ↓
Check Database Mode
    ├─→ Direct: SQL Query → Source DB
    └─→ API: Semantic Search → Vector DB ← ETL Pipeline ← Source DB
            ↓
       Return Results
            ↓
      Answer User
```

---

## Security Benefits Summary

| Aspect | Direct Mode | API Mode |
|--------|------------|----------|
| LLM DB Access | Yes (Full) | No (Vector DB only) |
| Risk of Injection | High | None |
| Real-time Data | Yes | No (interval-based) |
| Data Control | Limited | Complete |
| Freshness Window | Instant | Configurable |
| PII Exposure | High | Low |

---

## Troubleshooting

### "Vector DB not initialized"
```bash
# Check directory exists
ls -la ./chroma_data/

# Check permissions
chmod 755 ./chroma_data
```

### "ChromaDB module not found"
```bash
pip install chromadb
```

### "Ingestion job not running"
Check:
1. Database is in API mode (`query_mode='api'`)
2. At least one table is selected (`selected_tables` not empty)
3. Check logs for errors
4. Verify database connection works

### "No results from vector search"
1. Ingestion may not have completed yet
2. Check `last_sync` timestamp in database settings
3. Verify tables have data via direct query
4. Check vector DB collection exists

---

## Performance Tips

1. **Start small**: Select 2-3 key tables first
2. **Adjust sync intervals**: 
   - Product catalogs: 60-120 minutes
   - Orders: 30 minutes
   - Reference data: 1440 minutes (daily)
3. **Monitor ingestion**: Check job status regularly
4. **Manage storage**: Monitor `./chroma_data` size

---

## Next Features (Optional)

- Webhook-based triggers
- Multi-vector DB support
- Advanced chunking strategies
- Row-level access control
- Hybrid keyword + semantic search

---

## Support

For issues or questions:
1. Check `IMPLEMENTATION_SUMMARY.md` for technical details
2. Review `API_MEDIATED_RAG_GUIDE.md` for architecture
3. Check logs in your application console
4. Verify ChromaDB in `./chroma_data/`

---

**Ready to go!** 🚀

Implement the API endpoints above, and your API-Mediated RAG system is live!

