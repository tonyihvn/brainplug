import requests, json
BASE='http://127.0.0.1:5000'
resp = requests.post(BASE+'/api/chat/message', json={'message':'Hello, what LLM is active? Please respond with provider name.'})
print(resp.status_code)
try:
    print(json.dumps(resp.json(), indent=2))
except Exception:
    print(resp.text)
