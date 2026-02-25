#!/usr/bin/env python3
import requests as req
resp = req.get('http://localhost:11434/api/tags', timeout=2)
print(f"Status: {resp.status_code}")
print(f"Response JSON:")
import json
print(json.dumps(resp.json(), indent=2))
