import urllib.request, json
import os

# Override with AI_API_BASE when the API is not on the default Docker port.
BASE_URL = os.getenv("AI_API_BASE", "http://127.0.0.1:8100")
API_KEY = "admin-key-001"


def test_endpoint(method, path, data=None):
    url = BASE_URL + path
    headers_dict = {"Content-Type": "application/json", "X-API-Key": API_KEY}

    try:
        if method == "GET":
            req = urllib.request.Request(url, headers=headers_dict, method="GET")
        elif method == "POST":
            body = json.dumps(data).encode("utf-8") if data else None
            req = urllib.request.Request(
                url, data=body, headers=headers_dict, method="POST"
            )

        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            try:
                result = json.loads(body)
            except:
                result = body
            return {"status": resp.status, "success": True, "data": result}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            result = json.loads(body)
        except:
            result = body
        return {"status": e.code, "success": False, "data": result}
    except Exception as e:
        return {"status": None, "success": False, "data": str(e)}


results = []

# Create a real conversation first so /memory has a valid UUID
_chat = test_endpoint("POST", "/chat", {"message": "مرحبا كيفك", "language": "ar"})
_chat_conv_id = "test123"
if isinstance(_chat, dict):
    _d = _chat.get("data")
    if isinstance(_d, dict):
        _chat_conv_id = _d.get("conversation_id", "test123")

results.append(("GET /agents (admin)", test_endpoint("GET", "/agents")))
results.append(("GET /settings (admin)", test_endpoint("GET", "/settings")))
results.append(
    (
        "GET /memory (admin)",
        test_endpoint("GET", f"/memory?conversation_id={_chat_conv_id}"),
    )
)

lines = []
lines.append("=" * 50)
lines.append("ADMIN TEST RESULTS:")
lines.append("=" * 50)

all_passed = True
for name, result in results:
    status = result.get("status")
    success = result.get("success")
    data = result.get("data")

    if success and status == 200:
        status_str = "PASS"
    else:
        status_str = f"FAIL({status})"

    lines.append(f"{name}: {status_str}")

    if not (success and status == 200):
        all_passed = False
        lines.append(f"  Details: {str(data)[:200]}")

lines.append("=" * 50)
if all_passed:
    lines.append("ALL ADMIN TESTS PASSED!")
else:
    lines.append("SOME ADMIN TESTS FAILED")

with open(
    "C:/Users/user/Documents/Default Project/ai-assistant/test_admin_results.txt",
    "w",
    encoding="utf-8",
) as f:
    f.write("\n".join(lines))

print("\n".join(lines))
