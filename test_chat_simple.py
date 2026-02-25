#!/usr/bin/env python3
"""Test Ollama Mistral chat endpoint."""
import requests
import json
import time

BASE_URL = "http://localhost:5000"

print("\n" + "="*60)
print("Testing Ollama Mistral Chat")
print("="*60)

# Wait for server
print("\nWaiting for server...")
for i in range(15):
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=2)
        if response.status_code == 200:
            print("✓ Server ready!")
            break
    except:
        pass
    if i < 14:
        time.sleep(1)

# Test chat
print("\nSending message to chat endpoint...")
try:
    payload = {"message": "what is 2+2?"}
    print(f"Payload: {json.dumps(payload)}")
    
    response = requests.post(
        f"{BASE_URL}/api/chat/message",
        json=payload,
        timeout=30
    )
    
    print(f"\nStatus: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("\n✓ Success! Response:")
        print(json.dumps(data, indent=2))
        
        if data.get('success'):
            explanation = data['data'].get('explanation', 'N/A')
            action_type = data['data'].get('action_type', 'N/A')
            print(f"\n   Explanation: {explanation[:100]}...")
            print(f"   Action Type: {action_type}")
    else:
        print(f"\n✗ Failed!")
        print(response.text)
        
except Exception as e:
    print(f"\n✗ Error: {str(e)}")

print("\n" + "="*60)
