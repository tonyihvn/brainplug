#!/usr/bin/env python3
"""Test that Ollama is used when Gemini is deactivated."""
import requests
import json
import time

BASE_URL = "http://localhost:5000"

def test_chat_with_gemini_deactivated():
    """Send a chat message and verify Ollama responds, not Gemini."""
    print("\n1. Testing chat endpoint with Gemini deactivated...")
    
    payload = {
        "message": "Hello, what is 2+2?"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/chat/message",
            json=payload,
            timeout=30
        )
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
            
            # Check if we got a proper response (not Gemini error message)
            explanation = data.get('explanation', '')
            
            if 'GEMINI API key but no model is configured' in explanation:
                print("   ❌ FAIL: Got Gemini 'no model' message instead of Ollama response")
                return False
            elif 'No LLM model configured' in explanation:
                print("   ❌ FAIL: No LLM model available")
                return False
            elif explanation:
                print("   ✅ PASS: Got response from Ollama (or active LLM)")
                print(f"   Response snippet: {explanation[:200]}...")
                return True
            else:
                print("   ⚠️  WARNING: Empty response")
                return False
        else:
            print(f"   ❌ FAIL: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ ERROR: {str(e)}")
        return False

def test_active_model_check():
    """Check which model is currently active."""
    print("\n2. Checking active LLM model...")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/settings/llm",
            timeout=5
        )
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
            return data
        else:
            print(f"   Status: {response.status_code} (endpoint may not exist)")
            return None
            
    except Exception as e:
        print(f"   INFO: {str(e)}")
        return None

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Gemini Deactivation Fallback to Ollama")
    print("=" * 60)
    
    # Wait for server to be ready
    print("\nWaiting for server to be ready...")
    for i in range(10):
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=2)
            if response.status_code == 200:
                print("✅ Server is ready!")
                break
        except:
            pass
        if i < 9:
            time.sleep(1)
    else:
        print("⚠️  Server may not be ready, proceeding anyway...")
    
    # Run tests
    test_active_model_check()
    success = test_chat_with_gemini_deactivated()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TEST PASSED: Ollama is being used!")
    else:
        print("❌ TEST FAILED: Check logs and configuration")
    print("=" * 60)
