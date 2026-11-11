import os
import urllib.request, json

# Override with AI_API_BASE when the API is not on the default Docker port.
BASE_URL = os.getenv("AI_API_BASE", "http://127.0.0.1:8100")

data = json.dumps({"message": "مرحبا كيفك", "language": "ar"}).encode("utf-8")
req = urllib.request.Request(
    BASE_URL + "/chat",
    data=data,
    headers={"Content-Type": "application/json", "X-API-Key": os.getenv("API_KEY", "")},
    method="POST",
)

try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        print("Status:", resp.status)
        print("Success:", result.get("success"))
        print("Error:", result.get("error"))
        if result.get("answer"):
            print("Answer length:", len(result["answer"]))
except Exception as e:
    print("Error:", str(e))
