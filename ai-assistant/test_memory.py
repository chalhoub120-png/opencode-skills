import urllib.request, json

BASE_URL = "http://127.0.0.1:8001"
API_KEY = "admin-key-001"

def test_endpoint(method, path, data=None):
    url = BASE_URL + path
    headers_dict = {"Content-Type": "application/json", "X-API-Key": API_KEY}
    
    try:
        if method == "GET":
            req = urllib.request.Request(url, headers=headers_dict, method="GET")
        elif method == "POST":
            body = json.dumps(data).encode('utf-8') if data else None
            req = urllib.request.Request(url, data=body, headers=headers_dict, method="POST")
        
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode('utf-8')
            try:
                result = json.loads(body)
            except:
                result = body
            return {"status": resp.status, "success": True, "data": result}
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        try:
            result = json.loads(body)
        except:
            result = body
        return {"status": e.code, "success": False, "data": result}
    except Exception as e:
        return {"status": None, "success": False, "data": str(e)}

# اختبار الذاكرة بدون conversation_id
result = test_endpoint("GET", "/memory")
print("GET /memory (no conv_id):", result.get("status"), result.get("success"))
print(result.get("data"))

print()

# اختبار الذاكرة مع conversation_id غير موجود
result = test_endpoint("GET", "/memory?conversation_id=nonexistent")
print("GET /memory (fake conv_id):", result.get("status"), result.get("success"))
print(result.get("data"))
