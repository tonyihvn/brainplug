#!/usr/bin/env python3
import requests
import json
import sys

try:
    response = requests.post(
        "http://localhost:5000/api/chat/message",
        json={"message": "what is 2+2?"},
        timeout=20
    )
    print(json.dumps({"status": response.status_code, "data": response.json() if response.status_code == 200 else response.text}, indent=2))
except Exception as e:
    print(json.dumps({"error": str(e)}))
    sys.exit(1)
