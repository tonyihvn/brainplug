# Quick Reference: Fixing Your Issues

## TL;DR - Do This Now

### 1. Start Backend (if not already running)
```bash
cd c:\Users\Ogochukwu\Desktop\PROJECTS\PYTHON\brainplug
python app.py
```

### 2. Run This in a New Terminal
```bash
cd c:\Users\Ogochukwu\Desktop\PROJECTS\PYTHON\brainplug
python scripts/test_query_mode_flow.py
```
**Expected:** All tests show [OK] ✅

### 3. Run This in the Same Terminal
```bash
python scripts/test_rag_generation_diagnostic.py
```
**Expected:** Shows tables_scanned > 0 and items_created > 0 ✅

### 4. Read This
- If tests pass: Issue is frontend caching. Do Ctrl+F5 hard refresh in browser.
- If query_mode test fails: Check server logs for [EDIT-DB] entries.
- If RAG test shows 0 tables: Check server logs for [SCHEMA] entries.

## What Changed

| Issue | Root Cause | What I Fixed |
|-------|-----------|--------------|
| Query Mode Not Saved | Missing field in backend | Added query_mode to new database settings |
| Zero Tables/Items | PostgreSQL schema detection | Enhanced schema extraction with explicit 'public' schema check |
| Server Restart | Expected Flask behavior | Added documentation explaining this is normal |

## Where to Look for Answers

| Issue | File to Read |
|-------|--------------|
| "Help, what do I do now?" | [SOLUTION_SUMMARY.md](./SOLUTION_SUMMARY.md) |
| "Tests are failing, how do I debug?" | [DEBUGGING_GUIDE_ISSUES.md](./DEBUGGING_GUIDE_ISSUES.md) |
| "What exactly changed?" | [CHANGES_SUMMARY.md](./CHANGES_SUMMARY.md) |
| "I want to understand the logging" | [CHANGES_SUMMARY.md](./CHANGES_SUMMARY.md#summary-of-logging-prefixes) |

## Key Server Log Prefixes to Watch

When you connect a database, watch the Flask terminal for:

```
[DB-CONNECT]     ← Query mode submission
[EDIT-DB]        ← Saving existing setting
[NEW-DB]         ← Creating new setting
[SCHEMA]         ← Table discovery
[RAG-POPULATE]   ← RAG item creation
[AUTO-RAG]       ← Final statistics
```

If you see these prefixes, the enhanced logging is working!

## Success Checklist

- [ ] test_query_mode_flow.py passes all 4 steps
- [ ] test_rag_generation_diagnostic.py shows tables_scanned > 0
- [ ] Server logs show [DB-CONNECT] entries
- [ ] After browser refresh (Ctrl+F5), settings show correct query mode
- [ ] Database shows "Vector DB" badge in connected databases table (not "Direct Query")

## Common Issues

**Issue:** Tests pass but UI still wrong
→ Do hard refresh: **Ctrl+F5** in browser (not just F5)

**Issue:** Query mode test fails with "connection error"
→ Make sure Flask app is running: `python app.py`

**Issue:** RAG test shows 0 tables
→ Check server logs for [SCHEMA] entries starting with "⚠️ WARNING"

**Issue:** Server keeps showing "Loading configuration..."
→ This is normal! Flask development server restarts when .env changes. It will settle after 5-10 seconds.

## Need More Help?

1. **Read [DEBUGGING_GUIDE_ISSUES.md](./DEBUGGING_GUIDE_ISSUES.md)** - Complete debugging guide with all options
2. **Check server logs** - Look for log prefixes [DB-CONNECT], [SCHEMA], [RAG-POPULATE]
3. **Run test scripts** - They provide specific pass/fail feedback for each component
4. **Check browser console** - Press F12, go to Console tab, look for [DB-FORM] entries

## Before You Report a Bug

Make sure you:
1. Have run both test scripts and shared their output
2. Have shown the server logs (screenshot of Flask terminal)
3. Have tried hard refresh (Ctrl+F5) in browser
4. Have verified your database has tables (if using PostgreSQL)

This will help me understand exactly what's happening.
