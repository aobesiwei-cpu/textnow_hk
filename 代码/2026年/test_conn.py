import urllib.request
import urllib.error
import base64

url = "http://127.0.0.1:8899/"
# 带上 Basic Auth 认证
creds = base64.b64encode(b"admin:admin123").decode()
req = urllib.request.Request(url, headers={"Authorization": f"Basic {creds}"})
try:
    resp = urllib.request.urlopen(req, timeout=5)
    content = resp.read(500)
    print(f"STATUS: {resp.status}")
    print(f"CONTENT (first 500 bytes):\n{content.decode('utf-8', errors='replace')}")
except urllib.error.HTTPError as e:
    print(f"HTTP ERROR: {e.code} - {e.reason}")
    print(f"Headers: {e.headers}")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
