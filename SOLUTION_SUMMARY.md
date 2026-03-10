# Solution: Fixing Query Mode, RAG Generation, and Server Restart Issues

## What Was Done

I've enhanced the application with comprehensive logging and diagnostic tools to help identify and resolve the issues you reported:

### Backend Enhancements (settings_service.py)
✅ Added detailed logging for query_mode tracking
✅ Added verification step after saving database settings
✅ Enhanced RAG generation logging with [RAG-POPULATE] prefix
✅ Improved error messages for specific failure scenarios

### Schema Extraction Enhancements (database.py)
✅ Enhanced PostgreSQL schema detection
✅ Added detailed [SCHEMA] logging for debugging
✅ Added fallback logic for schema detection

### New Diagnostic Tools
✅ Created `scripts/test_query_mode_flow.py` - Tests query_mode persistence
✅ Created `scripts/test_rag_generation_diagnostic.py` - Tests RAG generation
✅ Created `DEBUGGING_GUIDE_ISSUES.md` - Complete debugging guide

## What You Need to Do

### 1. Verify Your Setup

First, make sure your backend is running and accessible:

```bash
cd c:\Users\Ogochukwu\Desktop\PROJECTS\PYTHON\brainplug

# If you haven't already, activate your Python environment
# Then start the Flask app
python app.py
```

You should see logs starting with timestamps and [INFO] levels.

### 2. Run the Diagnostic Tests

While the Flask app is running in one terminal, open another terminal and run:

```bash
cd c:\Users\Ogochukwu\Desktop\PROJECTS\PYTHON\brainplug

# Test 1: Query Mode Flow
python scripts/test_query_mode_flow.py

# Expected output should show all tests passing
```

**If this passes:** Query mode is being saved correctly. The issue you're seeing might be:
- Browser caching (try Ctrl+F5 hard refresh)
- Form not loading saved value correctly
- Frontend logic issue

**If this fails:** The backend isn't preserving query_mode. Check server logs for [EDIT-DB] entries.

### 3. Run the RAG Generation Test

```bash
cd c:\Users\Ogochukwu\Desktop\PROJECTS\PYTHON\brainplug
python scripts/test_rag_generation_diagnostic.py
```

This creates a test SQLite database and attempts RAG generation.

**If this shows tables_scanned=0:** 
- The schema extraction is failing
- Check server logs for [SCHEMA] entries
- This is the likely cause of your "0 tables, 0 items" issue

**If this shows tables_scanned > 0:** 
- Schema extraction works, so your database might just be empty
- Or there might be a specific issue with your PostgreSQL connection

### 4. Monitor Server Logs

The most important step is **watching the server logs** when you test things in the app:

1. Keep the Flask server terminal visible
2. Create a new database connection in the UI
3. Watch the logs for these patterns:

**For query_mode:**
```
[DB-CONNECT] Settings: query_mode=api, is_active=true
[EDIT-DB] Verification after save: query_mode=api
```

**For RAG generation:**
```
[SCHEMA] ========== SCHEMA EXTRACTION STARTING ==========
[SCHEMA] Initial get_table_names() returned N tables
[RAG-POPULATE] ✓ Extracted schema with N tables
```

If you see warnings like `[SCHEMA] ⚠️ No tables found after all attempts`, this confirms schema detection is failing.

### 5. Check Your PostgreSQL Database

If you're using PostgreSQL, verify your database actually has tables:

```bash
# Connect to your PostgreSQL database
psql -h localhost -U postgres -d your_database

# Then in psql:
\dt
```

This lists all tables. If you see no tables, that's why RAG generation shows 0 items!

## Understanding the Server Restart Behavior

The "Loading configuration..." message you see is **expected behavior** in development:

1. You connect a database
2. Backend saves DATABASE_URL to `.env` file
3. Flask's Werkzeug development server detects the `.env` change
4. Server auto-restarts (this is the "Loading..." message)
5. After ~5 seconds, server is back up and responsive

**This is normal and will NOT happen in production.** You can prevent it in development by:

```bash
# Instead of: python app.py
# Use: FLASK_ENV=development python app.py --no-reload
```

But the auto-restart behavior is actually helpful during development.

## Interpreting Success

### Success Indicators

✅ **Query Mode Working:**
- Test script shows all steps passing
- Server logs show query_mode values being tracked
- After refreshing the page, the setting shows "Vector DB" badge
- When you re-edit the setting, query_mode field shows "API Query"

✅ **RAG Generation Working:**
- Test script shows tables_scanned > 0
- Test script shows items_created > 0
- When you connect a database, modal shows correct table/item counts
- No zeros in the statistics

✅ **App Behavior:**
- "Loading configuration..." appears briefly (expected)
- App is responsive after loading
- Database shows as "API Query" in the connected databases table

## If Tests Pass but UI Shows Issues

If the test scripts pass but the UI still shows incorrect data:

1. **Hard refresh the browser:** Ctrl+F5 (not just F5)
2. **Clear browser cache:** DevTools → Application → Clear storage
3. **Check browser console:** F12 → Console tab for errors
4. **Check that you're looking at the right database:** Settings → RAG tab

## Next Steps Based on Test Results

### If test_query_mode_flow.py Fails
📍 **Issue Location:** Backend settings save/retrieve
📍 **What to Check:**
- Server logs for [EDIT-DB] entries
- Verify rag_database.py is correctly saving ALL fields
- Check if using Qdrant/ChromaDB or JSON fallback

### If test_rag_generation_diagnostic.py Fails with "0 tables"
📍 **Issue Location:** Schema extraction
📍 **What to Check:**
- Server logs for [SCHEMA] entries
- If using PostgreSQL: Verify 'public' schema exists and has tables
- If using MySQL: Verify database is not empty
- If using SQLite: Verify database file path is correct

### If Both Tests Pass but UI Shows Issues
📍 **Issue Location:** Frontend or browser state
📍 **What to Check:**
- Browser console for JavaScript errors
- whether page is loading fresh data or showing cached data
- Whether form is properly loading saved settings on edit

## Performance Note

RAG generation might take a few seconds depending on:
- Database size (number of tables)
- Number of columns per table
- Access to sample data from each table
- RAG vector database performance

This is normal. The "Loading configuration..." message will be displayed until RAG generation completes.

## Questions or Issues?

Try this methodical approach:

1. Run the test scripts - they'll tell you if backend is working
2. Check server logs - they'll tell you where the failure is
3. Check browser logs - they'll tell you if frontend has issues
4. Verify your database - it might just be empty!

The enhanced logging should make it clear exactly what's happening and where the real issue is.
