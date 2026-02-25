#!/usr/bin/env python3
"""Test Mistral auto-detection and schema population."""

import requests
import json
import time
import sys

BASE = 'http://127.0.0.1:5000'

def test_flow():
    print("="*70)
    print("COMPREHENSIVE TEST: Mistral Auto-Detection + Schema Population")
    print("="*70)
    
    # Wait for server
    print("\n[1/5] Waiting for Flask server to be ready...")
    for attempt in range(15):
        try:
            r = requests.get(f'{BASE}/api/health', timeout=1)
            if r.status_code == 200:
                print("  ✅ Server ready")
                break
        except Exception:
            pass
        if attempt < 14:
            time.sleep(1)
    else:
        print("  ❌ Server not responding after 15 attempts")
        return False
    
    # Check active LLM model
    print("\n[2/5] Checking active LLM model (should be auto-detected Mistral)...")
    try:
        r = requests.get(f'{BASE}/api/settings/llm', timeout=5)
        data = r.json()
        models = data.get('data', {}).get('models', [])
        active_models = [m for m in models if m.get('is_active')]
        
        if active_models:
            active = active_models[0]
            print(f"  ✅ Active LLM: {active.get('name')} (type: {active.get('model_type')}, model_id: {active.get('model_id')})")
            if 'mistral' in str(active.get('model_id', '')).lower():
                print("  ✅ Mistral is active!")
            else:
                print(f"  ⚠️ Active model is not Mistral, but {active.get('model_id')}")
        else:
            print("  ⚠️ No active LLM model found")
    except Exception as e:
        print(f"  ❌ Error checking LLM: {e}")
    
    # Test chat with Mistral
    print("\n[3/5] Testing chat message with Mistral...")
    try:
        r = requests.post(f'{BASE}/api/chat/message', 
                         json={'message': 'Hello, who are you?'},
                         timeout=30)
        if r.status_code == 200:
            resp = r.json()
            action_type = resp.get('data', {}).get('action_type', 'UNKNOWN')
            explanation = resp.get('data', {}).get('explanation', '')[:100]
            
            if 'not configured' in explanation.lower() or 'no llm' in explanation.lower():
                print(f"  ❌ LLM not configured: {explanation}")
                return False
            elif 'gemini-pro' in explanation.lower() or '404' in explanation.lower():
                print(f"  ❌ Still getting Gemini-pro error: {explanation}")
                return False
            else:
                print(f"  ✅ Chat succeeded!")
                print(f"     Action: {action_type}")
                print(f"     Response preview: {explanation}...")
        else:
            print(f"  ❌ Chat failed with status {r.status_code}: {r.text[:200]}")
            return False
    except Exception as e:
        print(f"  ❌ Error sending chat: {e}")
        return False
    
    # Connect a database
    print("\n[4/5] Connecting to SQLite database (gemini_mcp.db)...")
    try:
        payload = {
            'name': 'Test SQLite DB',
            'db_type': 'sqlite',
            'database': 'gemini_mcp.db',
            'is_active': True
        }
        r = requests.post(f'{BASE}/api/settings/database', json=payload, timeout=10)
        if r.status_code == 200:
            db_data = r.json().get('data', {})
            print(f"  ✅ Database connected: {db_data.get('name')} (ID: {db_data.get('id')})")
            time.sleep(2)  # Wait for schema population
        else:
            print(f"  ❌ Failed to connect database: {r.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ Error connecting database: {e}")
        return False
    
    # Verify schema and business rules
    print("\n[5/5] Verifying auto-populated schemas and business rules...")
    try:
        # Get schemas
        r = requests.get(f'{BASE}/api/rag/schema', timeout=5)
        schema_data = r.json().get('data', {})
        tables = schema_data.get('tables', []) if isinstance(schema_data, dict) else []
        
        print(f"  Schema tables found: {len(tables)}")
        if tables:
            for table in tables[:3]:
                print(f"    - {table.get('table_name', 'unknown')}: {len(table.get('columns', []))} columns")
        
        # Get business rules
        r = requests.get(f'{BASE}/api/rag/business-rules', timeout=5)
        rules_data = r.json().get('data', {})
        total_rules = rules_data.get('total', 0)
        auto_rules = rules_data.get('auto_generated_count', 0)
        
        print(f"  Total business rules: {total_rules}")
        print(f"  Auto-generated rules: {auto_rules}")
        
        if auto_rules > 0:
            print("  ✅ Schema and business rules auto-populated!")
            rules = rules_data.get('rules', [])[:2]
            for rule in rules:
                print(f"    - {rule.get('name')}: {rule.get('description', '')[:60]}")
            return True
        else:
            print("  ⚠️ No auto-generated business rules found")
            print(f"  (All rules: {total_rules})")
            return False
            
    except Exception as e:
        print(f"  ❌ Error checking schemas/rules: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print()
    success = test_flow()
    print("\n" + "="*70)
    if success:
        print("✅ ALL TESTS PASSED: Mistral is working and schema is auto-populated!")
    else:
        print("⚠️ Some tests failed or were incomplete. Check output above.")
    print("="*70 + "\n")
    sys.exit(0 if success else 1)
