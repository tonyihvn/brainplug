# LLM Configuration Persistence Fix

## Problem Summary
After configuring an LLM provider through the GUI form, the system would still display:
```
The system is not currently configured with a cloud LLM.
Action: NONE
```

Even though the LLM was saved in the database.

## Root Cause
**Data Store Mismatch**: The application was storing LLM configuration in two separate places without synchronization:

1. **SQL Database** (`LLMModel` table)
   - Where `SettingsService.update_llm_settings()` was saving configurations
   - Used by the API endpoints for CRUD operations

2. **RAG Database** (JSON file fallback in `instance/store/settings.json`)
   - Where `LLMService._ensure_active_model()` reads configurations
   - Used by the LLM service to find and initialize the active model

The flow was:
```
GUI Form → API → SettingsService → SQL DB ✓
                                      ↓
                                   LLMService → RAG DB ✗
                                   (reads from here, but data wasn't synced)
```

Result: The LLM configuration was saved to SQL but never synced to RAG, so LLMService couldn't find it.

## Solution Implemented

### 1. Updated `SettingsService.update_llm_settings()`
**File**: [backend/services/settings_service.py](backend/services/settings_service.py#L384-L470)

Now performs a dual-write when creating/updating LLM models:
- Save to SQL database (for API compatibility)
- **Also save to RAG database** (for LLMService to find)

**Key Changes**:
```python
# After saving to SQL DB, also save to RAG:
llm_data = {
    'id': str(model_id),
    'name': model.name,
    'model_type': model.model_type,
    # ... other fields
}
self.rag_db.save_setting(str(model_id), llm_data)
```

### 2. Updated `SettingsService.get_llm_settings()`
**File**: [backend/services/settings_service.py](backend/services/settings_service.py#L472-L492)

Now reads from RAG database first (preferred) with SQL fallback:
```
try:
  ✓ READ from RAG database (canonical source for LLMService)
catch:
  ✓ FALLBACK to SQL database (for backward compatibility)
```

### 3. Updated `SettingsService.delete_llm_model()`
**File**: [backend/services/settings_service.py](backend/services/settings_service.py#L494-L515)

Now deletes from both stores:
- Delete from SQL database
- **Also delete from RAG database**

## Data Flow After Fix

### Configuration Storage
```
GUI Form 
  ↓
API Endpoint (/api/settings/llm POST)
  ↓
SettingsService.update_llm_settings()
  ├→ SQL Database (LLMModel table)
  └→ RAG Database (settings.json) ← LLMService reads from here
  
After save: llm_service._ensure_active_model() refreshes
```

### Configuration Retrieval
```
LLMService.__init__()
  ↓
_ensure_active_model()
  ↓
rag_db.get_all_database_settings()
  ↓
Finds active model & initializes appropriate client
(Gemini, Claude, Ollama, etc)
```

## Testing

Run the included test to verify the fix:
```bash
python test_llm_sync.py
```

**What the test verifies**:
1. ✓ LLM models are created and saved to RAG database
2. ✓ LLMService can find and initialize the active model
3. ✓ Updates are properly synced to both stores
4. ✓ LLMService instances can discover configuration after restart
5. ✓ Deletion removes from both stores

**Result**: All 7 tests passed ✓

## Affected Code

### Modified Files
1. [backend/services/settings_service.py](backend/services/settings_service.py)
   - `update_llm_settings()` - Added RAG sync
   - `get_llm_settings()` - Added RAG-first logic
   - `delete_llm_model()` - Added RAG deletion

### Untouched (Already Working)
- [backend/services/llm_service.py](backend/services/llm_service.py)
  - `_ensure_active_model()` already reads from RAG
  - App.py already calls refresh after settings update

## Backward Compatibility

✓ **Fully backward compatible**:
- SQL database remains as secondary source
- Existing configurations in SQL are still accessible
- Graceful fallback if RAG database unavailable
- No breaking changes to API contracts

## Verification Steps for Users

After applying this fix, LLM configuration should work as follows:

1. **Configure LLM in GUI** (Settings → LLM Settings)
2. **Save Configuration**
3. **Send a Chat Message**
4. **Expected Result**: The LLM processes the message (no "not configured" error)

If you still see the error, verify:
- LLM model is marked as `is_active: true`
- API key is properly set (for cloud LLMs)
- Model ID is valid
- App was restarted after configuration (or refresh via API was called)

## Files Created for Testing
- `test_llm_sync.py` - Comprehensive test suite for the fix
- `check_rag_settings.py` - Quick debugging tool
