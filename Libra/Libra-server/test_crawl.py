import urllib.request
import json

url = 'http://127.0.0.1:5187/api/assets/scan/domain'
data = json.dumps({'domain': 'qau.edu.cn'}).encode()
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        print('Status:', resp.status)
        print('Body:', resp.read().decode())
except urllib.error.HTTPError as e:
    print('HTTP Error:', e.code, e.read().decode())
except Exception as e:
    print('Error:', e)
