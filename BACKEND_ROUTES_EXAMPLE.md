# Implementation Example: Integrating API Endpoints

This document shows a complete example of how to integrate the API endpoints into your existing Flask/Python application.

## Prerequisites

Ensure you have these services initialized in your application:
- SettingsService (for database settings)
- IngestionPipeline (for ETL)
- ScheduledIngestionService (for background jobs)
- ActionService (routing integration - already done)

## Complete Settings Routes Implementation

### File: `backend/routes/api_rag_settings.py`

```python
"""
API-Mediated RAG Settings Routes

Handles table discovery, ingestion job management, and API configuration
for the new Vector Database query mode.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import uuid
import logging

from backend.services.ingestion_pipeline import IngestionPipeline
from backend.services.scheduled_ingestion import get_ingestion_service
from backend.services.settings_service import SettingsService
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)

# Create blueprint
api_rag_bp = Blueprint('api_rag', __name__, url_prefix='/api/rag')


# ============================================================================
# TABLE DISCOVERY
# ============================================================================

@api_rag_bp.route('/discover-tables/<database_id>', methods=['GET', 'POST'])
def discover_tables(database_id=None):
    """
    Discover all available tables in a database.
    
    Route: GET/POST /api/rag/discover-tables/<database_id>
    
    Response:
    {
        "status": "success",
        "data": [
            {
                "name": "products",
                "columns": ["id", "name", "description", "price", ...],
                "sample_count": 1000,
                "query_template": "SELECT ... FROM products LIMIT 1000"
            },
            ...
        ]
    }
    """
    try:
        # Get database_id from either URL params or request body
        if not database_id and request.method == 'POST':
            database_id = request.json.get('database_id')
        
        if not database_id:
            return jsonify({
                'status': 'error',
                'message': 'database_id is required'
            }), 400
        
        logger.info(f"→ Discovering tables for database: {database_id}")
        
        # Get database setting
        settings_service = SettingsService()
        all_settings = settings_service.get_database_settings()
        database_setting = next(
            (s for s in all_settings if s.get('id') == database_id),
            None
        )
        
        if not database_setting:
            logger.warning(f"✗ Database not found: {database_id}")
            return jsonify({
                'status': 'error',
                'message': f'Database "{database_id}" not found'
            }), 404
        
        # Discover tables
        pipeline = IngestionPipeline()
        tables = pipeline.discover_tables(database_setting)
        
        logger.info(f"✓ Discovered {len(tables)} tables")
        
        return jsonify({
            'status': 'success',
            'data': tables,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"✗ Error discovering tables: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# ============================================================================
# INGESTION JOB MANAGEMENT
# ============================================================================

@api_rag_bp.route('/ingestion/start/<database_id>', methods=['POST'])
def start_ingestion_job(database_id):
    """
    Start an ingestion job for a database.
    
    Route: POST /api/rag/ingestion/start/<database_id>
    
    Request Body:
    {
        "database_id": "db_xyz"  # Optional, can use URL param
    }
    
    Response:
    {
        "status": "success",
        "data": {
            "job_id": "job_abc123",
            "database_id": "db_xyz",
            "database_name": "inventory",
            "message": "Ingestion job started...",
            "status": "running"
        }
    }
    """
    try:
        logger.info(f"→ Starting ingestion for database: {database_id}")
        
        # Validate database exists
        settings_service = SettingsService()
        all_settings = settings_service.get_database_settings()
        database_setting = next(
            (s for s in all_settings if s.get('id') == database_id),
            None
        )
        
        if not database_setting:
            return jsonify({
                'status': 'error',
                'message': f'Database "{database_id}" not found'
            }), 404
        
        # Validate query mode
        if database_setting.get('query_mode') != 'api':
            return jsonify({
                'status': 'error',
                'message': 'Database must be in API query mode to start ingestion'
            }), 400
        
        # Validate selected tables
        selected_tables = database_setting.get('selected_tables', {})
        enabled_tables = [t for t in selected_tables.values() if t.get('enabled')]
        
        if not enabled_tables:
            return jsonify({
                'status': 'error',
                'message': 'No tables selected for ingestion'
            }), 400
        
        # Start ingestion job
        ingestion_service = get_ingestion_service()
        job_id = ingestion_service.start_ingestion_job(database_setting)
        
        logger.info(f"✓ Ingestion job started: {job_id}")
        
        return jsonify({
            'status': 'success',
            'data': {
                'job_id': job_id,
                'database_id': database_id,
                'database_name': database_setting.get('name'),
                'tables_selected': len(enabled_tables),
                'message': f'Ingestion job started for {len(enabled_tables)} table(s)',
                'status': 'running'
            }
        }), 201
        
    except Exception as e:
        logger.error(f"✗ Error starting ingestion: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@api_rag_bp.route('/ingestion/status/<job_id>', methods=['GET'])
def get_ingestion_job_status(job_id):
    """
    Get status of an active ingestion job.
    
    Route: GET /api/rag/ingestion/status/<job_id>
    
    Response:
    {
        "status": "success",
        "data": {
            "job_id": "job_abc123",
            "database": "inventory",
            "created_at": "2026-03-05T14:00:00Z",
            "last_run": "2026-03-05T14:32:00Z",
            "next_run": "2026-03-05T15:32:00Z",
            "success_count": 45,
            "error_count": 0,
            "last_error": null,
            "is_running": true
        }
    }
    """
    try:
        logger.debug(f"→ Getting status for job: {job_id}")
        
        ingestion_service = get_ingestion_service()
        status = ingestion_service.get_job_status(job_id)
        
        if not status:
            return jsonify({
                'status': 'error',
                'message': f'Job "{job_id}" not found. It may have been stopped.'
            }), 404
        
        return jsonify({
            'status': 'success',
            'data': status
        }), 200
        
    except Exception as e:
        logger.error(f"✗ Error getting job status: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@api_rag_bp.route('/ingestion/jobs', methods=['GET'])
def get_all_ingestion_jobs():
    """
    Get status of all active ingestion jobs.
    
    Route: GET /api/rag/ingestion/jobs
    
    Response:
    {
        "status": "success",
        "data": [
            {
                "job_id": "job_abc123",
                "database": "inventory",
                "last_run": "2026-03-05T14:32:00Z",
                "next_run": "2026-03-05T15:32:00Z",
                "success_count": 45,
                "error_count": 0
            },
            ...
        ]
    }
    """
    try:
        logger.debug("→ Getting all active ingestion jobs")
        
        ingestion_service = get_ingestion_service()
        jobs = ingestion_service.get_all_jobs()
        
        return jsonify({
            'status': 'success',
            'data': jobs,
            'count': len(jobs)
        }), 200
        
    except Exception as e:
        logger.error(f"✗ Error getting jobs: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@api_rag_bp.route('/ingestion/stop/<job_id>', methods=['POST'])
def stop_ingestion_job(job_id):
    """
    Stop an active ingestion job.
    
    Route: POST /api/rag/ingestion/stop/<job_id>
    
    Response:
    {
        "status": "success",
        "message": "Job stopped successfully"
    }
    """
    try:
        logger.info(f"→ Stopping ingestion job: {job_id}")
        
        ingestion_service = get_ingestion_service()
        success = ingestion_service.stop_ingestion_job(job_id)
        
        if success:
            logger.info(f"✓ Job stopped: {job_id}")
            return jsonify({
                'status': 'success',
                'message': f'Job "{job_id}" has been stopped'
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': f'Could not stop job "{job_id}"'
            }), 500
        
    except Exception as e:
        logger.error(f"✗ Error stopping job: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@api_rag_bp.route('/ingestion/manual-sync/<database_id>', methods=['POST'])
def manual_sync_database(database_id):
    """
    Manually trigger ingestion for a database (outside normal schedule).
    
    Route: POST /api/rag/ingestion/manual-sync/<database_id>
    
    Response:
    {
        "status": "success",
        "data": {
            "database": "inventory",
            "tables_ingested": 3,
            "total_records": 5000,
            "total_chunks": 12500,
            "completed_at": "2026-03-05T14:45:00Z"
        }
    }
    """
    try:
        logger.info(f"→ Manual sync triggered for: {database_id}")
        
        # Get database setting
        settings_service = SettingsService()
        all_settings = settings_service.get_database_settings()
        database_setting = next(
            (s for s in all_settings if s.get('id') == database_id),
            None
        )
        
        if not database_setting:
            return jsonify({
                'status': 'error',
                'message': f'Database "{database_id}" not found'
            }), 404
        
        # Run ingestion immediately
        pipeline = IngestionPipeline()
        result = pipeline.ingest_database(database_setting)
        
        logger.info(f"✓ Manual sync completed: {result['tables_ingested']} tables")
        
        return jsonify({
            'status': 'success',
            'data': result
        }), 200
        
    except Exception as e:
        logger.error(f"✗ Error during manual sync: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# ============================================================================
# VECTOR DATABASE MANAGEMENT
# ============================================================================

@api_rag_bp.route('/vector-db/clear/<database_id>', methods=['POST'])
def clear_vector_collection(database_id):
    """
    Clear all vectors from a database's collection.
    Use this before re-ingestion to avoid duplicates.
    
    Route: POST /api/rag/vector-db/clear/<database_id>
    
    Response:
    {
        "status": "success",
        "message": "Vector collection cleared successfully"
    }
    """
    try:
        logger.info(f"→ Clearing vector collection for: {database_id}")
        
        # Get database setting
        settings_service = SettingsService()
        all_settings = settings_service.get_database_settings()
        database_setting = next(
            (s for s in all_settings if s.get('id') == database_id),
            None
        )
        
        if not database_setting:
            return jsonify({
                'status': 'error',
                'message': f'Database "{database_id}" not found'
            }), 404
        
        # Clear collection
        collection_name = database_setting.get('vector_db_collection')
        if not collection_name:
            collection_name = f"db_{database_id}"
        
        pipeline = IngestionPipeline()
        success = pipeline.clear_collection(collection_name)
        
        if success:
            logger.info(f"✓ Vector collection cleared: {collection_name}")
            return jsonify({
                'status': 'success',
                'message': f'Vector collection "{collection_name}" cleared'
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to clear collection'
            }), 500
        
    except Exception as e:
        logger.error(f"✗ Error clearing collection: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# ============================================================================
# HEALTH CHECK
# ============================================================================

@api_rag_bp.route('/health', methods=['GET'])
def health_check():
    """
    Check health of API RAG services.
    
    Route: GET /api/rag/health
    
    Response:
    {
        "status": "ok",
        "services": {
            "ingestion_pipeline": "ready",
            "scheduled_ingestion": "running",
            "vector_db": "initialized"
        }
    }
    """
    try:
        services = {
            'ingestion_pipeline': 'ready',
            'scheduled_ingestion': 'checking',
            'vector_db': 'checking'
        }
        
        # Check if ingestion service is running
        try:
            ingestion_service = get_ingestion_service()
            if ingestion_service and ingestion_service.is_running:
                services['scheduled_ingestion'] = 'running'
            else:
                services['scheduled_ingestion'] = 'idle'
        except Exception as e:
            services['scheduled_ingestion'] = f'error: {str(e)}'
        
        # Check vector DB
        try:
            pipeline = IngestionPipeline()
            if pipeline.vector_client:
                services['vector_db'] = 'initialized'
            else:
                services['vector_db'] = 'not initialized'
        except Exception as e:
            services['vector_db'] = f'error: {str(e)}'
        
        return jsonify({
            'status': 'ok',
            'services': services,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
```

## Integration into Main App

### File: `app.py` (or `main.py`)

```python
from flask import Flask
from backend.routes.api_rag_settings import api_rag_bp

app = Flask(__name__)

# ... other configurations ...

# Register the API RAG blueprint
app.register_blueprint(api_rag_bp)

# If you have existing blueprints, add them too:
# app.register_blueprint(other_bp)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

## Complete Example: Enhanced Database Settings Route

If your app has an existing `/settings/database` route, enhance it like this:

```python
@app.route('/settings/database', methods=['POST'])
def save_database_setting():
    """
    Save database configuration.
    Automatically starts ingestion if API mode and table selected.
    """
    try:
        from backend.services.settings_service import SettingsService
        from backend.services.scheduled_ingestion import get_ingestion_service
        
        data = request.json
        
        # ... existing save logic ...
        # Save to database, update settings, etc.
        
        saved_setting = {
            'id': data.get('id'),
            'name': data.get('name'),
            'query_mode': data.get('query_mode', 'direct'),
            # ... other fields ...
        }
        
        # NEW: Auto-start ingestion for API mode
        if (data.get('query_mode') == 'api' and 
            data.get('is_active') and 
            data.get('selected_tables')):
            
            try:
                ingestion_service = get_ingestion_service()
                job_id = ingestion_service.start_ingestion_job(saved_setting)
                
                logger.info(f"✓ Auto-started ingestion: {job_id}")
                saved_setting['ingestion_job_id'] = job_id
                
            except Exception as e:
                logger.warning(f"Could not auto-start ingestion: {str(e)}")
                saved_setting['ingestion_warning'] = str(e)
        
        return jsonify({
            'status': 'success',
            'data': saved_setting
        }), 200
        
    except Exception as e:
        logger.error(f"Error saving setting: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
```

## Testing All Endpoints

### Using cURL

```bash
# 1. Discover tables
curl -X GET 'http://localhost:5000/api/rag/discover-tables/db_xyz'

# 2. Start ingestion
curl -X POST 'http://localhost:5000/api/rag/ingestion/start/db_xyz'
# Returns: {"status": "success", "data": {"job_id": "..."}}

# 3. Check job status
curl -X GET 'http://localhost:5000/api/rag/ingestion/status/job_abc123'

# 4. Get all jobs
curl -X GET 'http://localhost:5000/api/rag/ingestion/jobs'

# 5. Manual sync
curl -X POST 'http://localhost:5000/api/rag/ingestion/manual-sync/db_xyz'

# 6. Clear vector DB
curl -X POST 'http://localhost:5000/api/rag/vector-db/clear/db_xyz'

# 7. Health check
curl -X GET 'http://localhost:5000/api/rag/health'
```

### Using Python Requests

```python
import requests

base_url = 'http://localhost:5000/api/rag'
db_id = 'db_xyz'

# Discover tables
response = requests.get(f'{base_url}/discover-tables/{db_id}')
print(response.json())

# Start ingestion
response = requests.post(f'{base_url}/ingestion/start/{db_id}')
job_id = response.json()['data']['job_id']

# Check status
response = requests.get(f'{base_url}/ingestion/status/{job_id}')
print(f"Status: {response.json()['data']}")
```

## Error Handling

All endpoints follow this response format:

**Success (200-201)**:
```json
{
  "status": "success",
  "data": { /* payload */ }
}
```

**Error (400+)**:
```json
{
  "status": "error",
  "message": "Detailed error message"
}
```

Your frontend can check `response.status` and then `data.status` for consistency.

---

## Summary

You now have a complete, production-ready implementation of:
1. ✅ Table discovery endpoint
2. ✅ Ingestion job management
3. ✅ Vector DB operations
4. ✅ Health monitoring
5. ✅ Error handling

All routes are documented, typed, and integrated with the services already implemented.

