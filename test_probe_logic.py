#!/usr/bin/env python3
"""Direct test of Ollama probe logic."""

import requests as req

mistral_found = False
for host in ['http://localhost:11434', 'http://127.0.0.1:11434']:
    print(f"Testing host: {host}")
    if mistral_found:
        print("  -> Already found, breaking")
        break
    for endpoint in ['/api/tags', '/models', '/api/models']:
        if mistral_found:
            print(f"  -> Already found, breaking inner")
            break
        url = f"{host}{endpoint}"
        try:
            resp = req.get(url, timeout=1)
            print(f"  {endpoint}: status {resp.status_code}")
            if resp.status_code != 200:
                continue
            
            data = resp.json()
            models = []
            if isinstance(data, dict) and 'tags' in data:
                models = data.get('tags', [])
            
            mistral_model = None
            for m in models:
                if 'mistral' in str(m).lower():
                    mistral_model = m
                    break
            
            if not mistral_model:
                print(f"    -> No mistral in models")
                continue
            
            print(f"  ✅ Found Mistral: {mistral_model}")
            mistral_found = True
            print(f"    Setting mistral_found = {mistral_found}, about to break")
            break
        except Exception as e:
            print(f"    Error: {e}")

print(f"\nFinal result: mistral_found = {mistral_found}")
