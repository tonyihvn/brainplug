#!/usr/bin/env python3
"""Test LLM service initialization and chat functionality"""

import requests
import json
import time
import sys

BASE_URL = 'http://127.0.0.1:5000'

print("=" * 80)
print(" " * 20 + "🤖 LLM SERVICE DIAGNOSTIC TEST")
print("=" * 80)

# Step 1: Check if Flask is running
print("\n[1/3] Checking Flask backend availability...")
try:
    response = requests.get(f'{BASE_URL}/health', timeout=2)
    print("  ✓ Flask backend is running")
except:
    try:
        response = requests.get(f'{BASE_URL}/', timeout=2)
        print("  ✓ Flask backend is running")
    except:
        print("  ✗ Flask backend is NOT running")
        print("  → Run: python app.py")
        sys.exit(1)

# Step 2: Get LLM settings to verify configuration
print("\n[2/3] Checking LLM configuration...")
try:
    response = requests.get(f'{BASE_URL}/api/settings/llm')
    if response.status_code == 200:
        data = response.json().get('data', [])
        active_llms = [m for m in data if m.get('is_active')]
        
        print(f"  Total LLM models: {len(data)}")
        if active_llms:
            active = active_llms[0]
            print(f"  ✓ Active LLM: {active.get('name')}")
            print(f"    Type: {active.get('model_type')}")
            print(f"    Model ID: {active.get('model_id', 'N/A')}")
            print(f"    API Key: {'✓ Set' if active.get('api_key') else '✗ Not set'}")
        else:
            print(f"  ⚠️  No active LLM configured")
            print(f"  → Available models: {', '.join(m.get('name') for m in data)}")
    else:
        print(f"  ✗ Failed to get LLM settings (status {response.status_code})")
except Exception as e:
    print(f"  ✗ Error: {e}")

# Step 3: Test chat endpoint
print("\n[3/3] Testing chat endpoint...")
try:
    payload = {
        'message': 'What is 2 + 2?',
        'conversation_id': None
    }
    response = requests.post(f'{BASE_URL}/api/chat/message', json=payload, timeout=30)
    
    print(f"  Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            result = data.get('data', {})
            print(f"  ✓ Chat response received")
            print(f"    Explanation: {result.get('explanation', '')[:80]}...")
            print(f"    Action Type: {result.get('action_type', 'NONE')}")
            
            # Check if response indicates LLM issue
            if 'not currently configured' in result.get('explanation', '').lower():
                print(f"\n  ❌ PROBLEM: LLM is configured but returning 'not configured' error")
                print(f"     Full response: {result.get('explanation', '')}")
            elif result.get('action_type') == 'NONE' and 'error' in result.get('explanation', '').lower():
                print(f"\n  ⚠️  WARNING: LLM returned an error")
                print(f"     Message: {result.get('explanation', '')}")
            else:
                print(f"\n  ✅ LLM is working correctly!")
        else:
            print(f"  ✗ API error: {data.get('error', 'Unknown error')}")
    elif response.status_code == 503:
        print(f"  ✗ LLM service not initialized (503)")
        data = response.json()
        print(f"  Error: {data.get('error', 'Unknown')}")
    else:
        print(f"  ✗ Unexpected status {response.status_code}")
        try:
            print(f"  Response: {response.json()}")
        except:
            print(f"  Response: {response.text[:200]}")
            
except requests.exceptions.Timeout:
    print(f"  ✗ Request timed out (30s)")
    print(f"  → LLM API may be slow or not responding")
except Exception as e:
    print(f"  ✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("""
If you see "not currently configured with a cloud LLM" error:

1. Go to Settings → LLM Settings
2. Check that you have an LLM configured:
   - Google Gemini (requires GEMINI_API_KEY)
   - Anthropic Claude (requires CLAUDE_API_KEY)  
   - Local Ollama (requires running Ollama service)

3. Ensure "is_active" checkbox is enabled for your LLM

4. Verify API keys are correct:
   - Gemini: Get key from https://aistudio.google.com
   - Claude: Get key from https://console.anthropic.com
   - Ollama: Check http://localhost:11434/api/models

5. Restart Flask: python app.py

If the issue persists, check Flask logs for:
  - "LLMService initialized"
  - "Active LLM: [model name]"
  - "_ensure_active_model:"
""")
print("=" * 80)
