"""Test RAG API endpoint."""
import requests
import json

BASE_URL = "http://localhost:5000"

# Get all RAG items
try:
    response = requests.get(f"{BASE_URL}/api/rag/items")
    data = response.json()
    
    if data.get('status') == 'success':
        items = data.get('data', [])
        print(f"✓ GET /api/rag/items: {len(items)} items returned")
        
        # Group by category
        categories = {}
        for item in items:
            cat = item.get('category', 'unknown')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)
        
        print(f"\nCategory breakdown:")
        for cat, items_list in sorted(categories.items()):
            print(f"  {cat}: {len(items_list)}")
        
        # Show first few items
        print(f"\nFirst 3 items:")
        for item in items[:3]:
            print(f"  - {item['title']} ({item['category']})")
    else:
        print(f"✗ Error: {data.get('message')}")
        
except Exception as e:
    print(f"✗ Request failed: {e}")
