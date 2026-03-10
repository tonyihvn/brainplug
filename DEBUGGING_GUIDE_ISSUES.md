# Debugging Guide: Server Restart, Query Mode, and RAG Generation Issues

## Problem Summary

The user reported three interrelated issues after connecting a PostgreSQL database with API Query mode:

1. **Server Restart** - App shows "Loading configuration..." after database connection
2. **Zero Tables** - RAG generation shows 0 tables scanned and 0 items created
3. **Query Mode Not Saved** - Database saved as "Direct Query" instead of "API Query"

## Root Cause Analysis

### Issue 1: Server Restart (Likely Benign)
This is probably **Flask development server auto-reloading**, which is normal behavior. The Werkzeug development server restarts when:
- `.env` file changes (DATABASE_URL is updated)
- Source files are modified
- Debug mode detects changes

**This is expected behavior** for development servers with auto-reload enabled. In production, this won't happen. The message "Loading configuration..." is just the frontend waiting for the server to respond after it restarts.

### Issue 2 & 3: Query Mode + RAG Generation
Multiple fixes have been applied to address these issues, but we need to verify they're working correctly. The test scripts will help diagnose this.

## What Was Fixed

### Backend Changes (settings_service.py)
1. Added `query_mode` field to new database settings dict
2. Enhanced logging with `[DB-CONNECT]`, `[EDIT-DB]`, `[NEW-DB]`, `[RAG-POPULATE]` prefixes
3. Added verification step after saving to confirm data persisted
4. Added detailed logging for query_mode tracking through the entire lifecycle

### Frontend Changes (DatabaseSettings.tsx)
1. Added port conversion from string to integer before sending
2. Added detailed console logging for debugging
3. Ensured query_mode is loaded when editing existing settings

### Database Schema Extraction (database.py)
1. Enhanced PostgreSQL schema detection to explicitly check "public" schema
2. Added `[SCHEMA]` logging at multiple points
3. Better fallback logic for empty table lists

## How to Diagnose

### Step 1: Run Query Mode Flow Test
This verifies that query_mode is properly saved and retrieved:

```bash
cd c:\Users\Ogochukwu\Desktop\PROJECTS\PYTHON\brainplug
python scripts/test_query_mode_flow.py
```

**Expected Output:**
```
[HH:MM:SS] [OK] SUCCESS: query_mode='api' in response
[HH:MM:SS] [OK] SUCCESS: query_mode='api' persisted in database
[HH:MM:SS] [OK] SUCCESS: query_mode='api' preserved after update
[HH:MM:SS] [OK] ALL TESTS PASSED
```

**If this fails:** The issue is in the backend persistence layer. Check server logs for `[EDIT-DB]` and `[NEW-DB]` entries.

### Step 2: Run RAG Generation Diagnostic Test
This verifies that RAG items are being created:

```bash
cd c:\Users\Ogochukwu\Desktop\PROJECTS\PYTHON\brainplug
python scripts/test_rag_generation_diagnostic.py
```

**Expected Output:**
```
[HH:MM:SS] [OK] Setting saved with id: xxxx-xxxx-xxxx
[HH:MM:SS] [OK] RAG Statistics: status=success, tables_scanned=3, items_created=3
```

**If you see zero tables/items:** The SQLAlchemy inspector is not finding tables. Check server logs for `[SCHEMA]` entries starting with `[SCHEMA] ==========`.

### Step 3: Check Server Logs
While running tests or using the app, check the terminal running `python app.py` for these log entries:

**For Query Mode Issues:**
```
[DB-CONNECT] Settings: name=..., query_mode=api, is_active=True
[EDIT-DB] Existing settings: query_mode=direct, is_active=False
[EDIT-DB] Incoming changes: query_mode=api, is_active=True
[EDIT-DB] After merge: query_mode=api, is_active=True
[EDIT-DB] Verification after save: query_mode=api
```

**For RAG Generation Issues:**
```
[SCHEMA] ========== SCHEMA EXTRACTION STARTING ==========
[SCHEMA] Connection string type: postgresql
[SCHEMA] Initial get_table_names() returned 5 tables
[RAG-POPULATE] ✓ Extracted schema with 5 tables
[RAG-POPULATE] Processing 5 tables for RAG generation...
[AUTO-RAG] RAG GENERATION COMPLETE for: PostgreSQL-Test
[AUTO-RAG] Tables Scanned: 5
[AUTO-RAG] Consolidated RAG Items Created: 5
```

## Browser Debugging

### Check Console Logs
1. Open browser DevTools (F12)
2. Go to Console tab
3. Look for lines starting with `[DB-FORM]`

```
[DB-FORM] Submitting database settings: {
  name: "my-db",
  query_mode: "api",
  is_active: true,
  db_type: "postgresql"
}

[DB-FORM] Response received: {
  query_mode: "api",
  is_active: true,
  rag_statistics: { status: "success" }
}
```

### Check Network Requests
1. Go to Network tab in DevTools
2. Filter by "database" to find API calls
3. Look at specific requests:
   - **POST /api/settings/database** - Check request body and response
   - **GET /api/settings/database** - Verify returned data includes query_mode

## What Each Test Script Does

### test_query_mode_flow.py

| Step | Testing | Expected |
|------|---------|----------|
| 1 | Save setting with query_mode='api' | Response includes query_mode='api' |
| 2 | Retrieve all settings | Retrieved setting has query_mode='api' |
| 3 | Update setting | After update, query_mode still 'api' |
| 4 | Cleanup | Delete test setting |

If any step fails, it tells you exactly which part of the flow is broken.

### test_rag_generation_diagnostic.py

| Step | Testing | Expected |
|------|---------|----------|
| 1 | Create SQLite test DB with 3 tables | Database created successfully |
| 2 | Save database with is_active=True | Response includes rag_statistics |
| 3 | Check RAG stats | tables_scanned=3, items_created=3 |
| 4 | Verify setting is still active | Setting remains active |

Each step provides detailed logging of what happened at the SQLAlchemy/schema extraction level.

## Common Issues and Solutions

### Issue: Query Mode Still Shows as "Direct Query"
**Check:** Server logs for `[EDIT-DB]` entries showing query_mode values
**Solution:** 
- If logs don't show query_mode at all, frontend isn't sending it. Check browser console.
- If logs show `Incoming changes: query_mode=api` but `Verification after save: query_mode=direct`, then RAG database save is not preserving the field. Check `rag_database.py`.

### Issue: Zero Tables Scanned
**Check:** Server logs for `[SCHEMA]` entries
**Possible Causes:**
1. **PostgreSQL default schema issue** - SQLAlchemy not looking in 'public' schema
   - Look for: `[SCHEMA] Available schemas: ['information_schema', 'pg_catalog', ...]`
   - If 'public' not listed, database is empty
   
2. **Connection string issue** - Wrong connection format for database type
   - Look for: `[DB-CONNECT] Settings: db_type=..., host=..., port=...`
   - Verify connection string format is correct
   
3. **Database permission issue** - User doesn't have permission to see tables
   - Check: Can you query `SELECT * FROM information_schema.tables` manually?

### Issue: Server Keeps Restarting During Connection
**This is normal!** Flask's development server auto-reloads when:
- `.env` DATABASE_URL is updated (happens on database connection)
- Files are modified

**To prevent this in development:**
```bash
# Disable auto-reload
FLASK_ENV=development WERKZEUG_RUN_MAIN=true python app.py
```

**In production:** This won't happen because production servers don't have auto-reload.

## Next Steps

1. **Run test_query_mode_flow.py** first to isolate the query_mode issue
2. **Check server logs** for messages starting with `[DB-CONNECT]`, `[EDIT-DB]`, `[NEW-DB]`
3. **Run test_rag_generation_diagnostic.py** to diagnose RAG generation
4. **Check browser console** for any front-end errors
5. **Verify database connectivity** by testing connection manually:
   ```bash
   psql -h localhost -U postgres -d your_database -c "SELECT table_name FROM information_schema.tables WHERE table_schema='public';"
   ```

## Log Level Configuration

If you need more detailed logs, update the logger level in `backend/utils/logger.py`:

```python
# Change from:
logger.setLevel(logging.INFO)

# To:
logger.setLevel(logging.DEBUG)
```

Debug level will include all `logger.debug()` calls, showing even more detail.

## Success Criteria

✅ **Query Mode Working:**
- test_query_mode_flow.py passes all steps
- Browser console shows query_mode='api' in request body
- Server logs show `[EDIT-DB] Verification after save: query_mode=api`
- Database settings table shows "Vector DB" badge instead of "Direct Query"

✅ **RAG Generation Working:**
- test_rag_generation_diagnostic.py shows tables_scanned > 0
- test_rag_generation_diagnostic.py shows items_created > 0
- Server logs show `[RAG-POPULATE] ✓ Extracted schema with N tables`
- Modal displays correct numbers instead of zeros

✅ **Server Behavior:**
- "Loading configuration..." message is normal and expected
- Server returns control within 5-10 seconds
- App is responsive after the message clears
