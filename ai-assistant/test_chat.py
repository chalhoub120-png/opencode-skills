import urllib.request, json

data = json.dumps({'message': 'مرحبا كيفك', 'language': 'ar'}).encode('utf-8')
req = urllib.request.Request(
    'http://127.0.0.1:8000/chat',
    data=data,
    headers={'Content-Type': 'application/json', 'X-API-Key': 'demo-key-001'},
    method='POST'
)

try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode('utf-8'))
        print('Status:', resp.status)
        print('Success:', result.get('success'))
        print('Error:', result.get('error'))
        if result.get('answer'):
            print('Answer length:', len(result['answer']))
except Exception as e:
    print('Error:', str(e))
