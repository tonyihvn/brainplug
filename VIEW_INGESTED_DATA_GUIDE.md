# How to View Embedded/Ingested Data

## Data Storage Locations

When you ingest data into the system, it's stored in multiple locations:

### 1. **Vector Database (Embeddings)**
- **Location**: `./chroma_data/` directory
- **Format**: ChromaDB vector database (DuckDB-based)
- **Content**: Semantic embeddings of your database records
- **Access**: Via RAG search in the chat interface

### 2. **Raw Data Backup (JSON)**
- **Location**: `instance/ingested_data/{database_id}/{table_name}/`
- **Format**: JSON files with raw records
- **Content**: Complete records extracted from source database
- **Structure**:
  ```
  instance/ingested_data/
  ├── {database_id_1}/
  │   ├── table_1_records.json      (raw records)
  │   ├── table_2_records.json      (raw records)
  │   └── table_1_embeddings.json   (embedding metadata)
  └── {database_id_2}/
      ├── table_A_records.json
      └── table_B_records.json
  ```

### 3. **Metadata & Configuration**
- **Location**: `instance/store/rag_items.json` and `instance/rag_db/`
- **Content**: Ingestion configuration, timing, and statistics
- **Format**: JSON

---

## Viewing Methods

### Method 1: Via File Explorer (Direct Inspection)

**Windows:**
```
1. Open File Explorer
2. Navigate to your brainplug folder
3. Go to → instance → ingested_data → {database_id}
4. Open any .json file with a text editor or VS Code
5. Review the raw embedded records
```

**Quick Command (PowerShell):**
```powershell
# View all ingested databases
Get-ChildItem instance/ingested_data -Directory

# View a specific table's data
Get-Content instance/ingested_data/{database_id}/{table_name}_records.json | jq '.' # if jq available
# Or simply:
Get-Content instance/ingested_data/{database_id}/{table_name}_records.json
```

### Method 2: Via Python Script

Create `view_ingested_data.py`:
```python
import json
import os
from pathlib import Path

INGESTED_DATA_DIR = Path("instance/ingested_data")

def view_ingested_data():
    """View all ingested data with nice formatting."""
    
    if not INGESTED_DATA_DIR.exists():
        print("No ingested data found yet.")
        print(f"Directory '{INGESTED_DATA_DIR}' does not exist.")
        return
    
    # List all databases
    databases = list(INGESTED_DATA_DIR.iterdir())
    
    if not databases:
        print("No databases have ingested data.")
        return
    
    print("\n" + "="*80)
    print("INGESTED DATA INVENTORY")
    print("="*80)
    
    for db_dir in databases:
        if not db_dir.is_dir():
            continue
        
        db_id = db_dir.name
        print(f"\n📦 Database: {db_id}")
        print("-" * 80)
        
        for file in db_dir.glob("*_records.json"):
            table_name = file.stem.replace("_records", "")
            
            try:
                with open(file, 'r') as f:
                    records = json.load(f)
                
                record_count = len(records) if isinstance(records, list) else 1
                
                # Show file size
                file_size_mb = file.stat().st_size / (1024 * 1024)
                
                print(f"  ✓ {table_name}")
                print(f"    - Records: {record_count}")
                print(f"    - Size: {file_size_mb:.2f} MB")
                
                # Show sample of first record
                if isinstance(records, list) and len(records) > 0:
                    sample = records[0]
                    keys = list(sample.keys())[:3]
                    print(f"    - Sample keys: {', '.join(keys)}")
                
            except Exception as e:
                print(f"  ✗ {table_name} - Error: {e}")
        
        print()

def view_table_data(database_id: str, table_name: str, limit: int = 5):
    """View specific table's ingested data."""
    
    file_path = INGESTED_DATA_DIR / database_id / f"{table_name}_records.json"
    
    if not file_path.exists():
        print(f"Data not found: {file_path}")
        return
    
    try:
        with open(file_path, 'r') as f:
            records = json.load(f)
        
        print(f"\n📋 Table: {table_name} (Database: {database_id})")
        print("="*80)
        print(f"Total Records: {len(records)}")
        print(f"Showing first {min(limit, len(records))} records:\n")
        
        for i, record in enumerate(records[:limit]):
            print(f"Record {i+1}:")
            print(json.dumps(record, indent=2))
            print("-" * 40)
            
    except Exception as e:
        print(f"Error reading data: {e}")

if __name__ == "__main__":
    # Show all ingested data summary
    view_ingested_data()
    
    # Uncomment to view specific table:
    # view_table_data("your_database_id", "your_table_name", limit=3)
```

**Run it:**
```bash
python view_ingested_data.py
```

### Method 3: Via Vector Database Browser

**ChromaDB Data:**
```python
import chromadb
from chromadb.config import Settings

# Connect to the vector DB
client = chromadb.Client(
    Settings(
        chroma_db_impl="duckdb+parquet",
        persist_directory="./chroma_data",
        anonymized_telemetry=False
    )
)

# List all collections
collections = client.list_collections()
print("Collections in Vector DB:")
for collection in collections:
    print(f"  - {collection.name}")
    print(f"    Items: {collection.count()}")
    
    # Get samples
    results = collection.get(limit=2)
    for i, doc in enumerate(results['documents']):
        print(f"    Sample {i+1}: {doc[:100]}...")
```

### Method 4: SQL Query (if using PostgreSQL backend)

```sql
-- Check what was last ingested
SELECT 
    database_id, 
    table_name, 
    records_ingested, 
    ingested_at
FROM ingestion_history
ORDER BY ingested_at DESC
LIMIT 10;
```

---

## Data Structure Example

### Sample ingested_data/records.json:
```json
[
  {
    "id": 123,
    "created_at": "2026-03-01T10:00:00",
    "name": "Account A",
    "balance": 5000.00,
    "status": "active"
  },
  {
    "id": 124,
    "created_at": "2026-03-02T11:30:00",
    "name": "Account B",
    "balance": 2500.00,
    "status": "pending"
  }
]
```

### Sample metadata:
```json
{
  "database_id": "8eb2f27a-a900-469f-8f24-e33752e24aaf",
  "table_name": "billing_account",
  "records_ingested": 487,
  "records_embedded": 487,
  "chunks_created": 1205,
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
  "ingested_at": "2026-03-06T10:30:45.123456",
  "processing_method": "semantic",
  "status": "completed"
}
```

---

## Common Tasks

### Count Total Ingested Records
```bash
# PowerShell
Get-ChildItem instance/ingested_data -Recurse -Filter "*_records.json" | 
  ForEach-Object { 
    $json = Get-Content $_.FullName | ConvertFrom-Json
    Write-Host "$($_.Directory.Name): $(($json | Measure-Object).Count) records"
  }
```

### Export Ingested Data
```python
import json
import shutil
from pathlib import Path

# Backup all ingested data
source = Path("instance/ingested_data")
destination = Path("backups/ingested_data_backup")
shutil.copytree(source, destination)
print(f"Backed up to {destination}")
```

### Delete Specific Table Data
```bash
# Remove a specific table's ingested data
rm -r instance/ingested_data/{database_id}/{table_name}_*

# Windows PowerShell
Remove-Item instance/ingested_data/{database_id}/{table_name}_* -Recurse
```

---

## Troubleshooting

### No Data Files Found
- **Cause**: Ingestion hasn't been run yet
- **Solution**: Go to Settings → Data Ingestion → Click "Start Ingestion"

### Files are Empty
- **Cause**: Tables had no records when ingested
- **Solution**: Check source database has data, then re-run ingestion

### Very Large Files
- **Cause**: Table had many records
- **Solution**: Consider filtering with WHERE conditions in extraction query

### Permission Denied
- **Cause**: File access issues
- **Solution**: Run as administrator or check file permissions

---

## Best Practices

1. **Regular Backups**: Copy `instance/ingested_data/` regularly
2. **Monitor Size**: Large files can slow down the system
3. **Archive Old Data**: Move completed ingestions to a backup location
4. **Version Control**: Keep track of when data was last updated
5. **Document Customizations**: Note any WHERE clause modifications made

---

## API Integration

To programmatically access ingested data:

```typescript
// Frontend example
const getIngestedData = async (databaseId: string) => {
  // Read from disk (requires backend endpoint)
  const response = await apiClient.post('/api/rag/ingest/status', {
    database_id: databaseId
  })
  return response.data.ingested_tables
}
```

---

## Summary

Your embedded data is stored in:
- **Vectors**: `./chroma_data/` (optimized for semantic search)
- **Raw Records**: `instance/ingested_data/{db_id}/{table}/ files (human-readable JSON)
- **Metadata**: `instance/store/rag_items.json` (configuration & stats)

Use the methods above to inspect, backup, or analyze your ingested data.
