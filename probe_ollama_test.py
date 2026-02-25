import requests, json
BASE='http://127.0.0.1:5000'
try:
    r = requests.get(BASE+'/api/settings/llm/ollama/models', timeout=5)
    print('status', r.status_code)
    print(json.dumps(r.json(), indent=2))
except Exception as e:
    print('error', e)
