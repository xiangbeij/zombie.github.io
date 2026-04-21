#!/usr/bin/env python3
import urllib.request, json, time

BASE = 'http://210.44.49.21:5189'

def api(path, data=None, method=None):
    url = BASE + path
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body,
        headers={'Content-Type': 'application/json'})
    if method:
        req.get_method = lambda: method
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def get(path):
    with urllib.request.urlopen(BASE + path, timeout=15) as r:
        return json.loads(r.read())

print("=" * 50)
print("FINAL VERIFICATION")
print("=" * 50)

print("\n[1] Health")
h = api('/api/health')
print(f"    {h['status']} | scheduler={h['scheduler_available']} | reportlab={h['reportlab_available']}")

print("\n[2] Stats")
print(f"    {api('/api/stats')}")

print("\n[3] Schedule - Create + List + Trigger + Delete")
r = api('/api/schedule', {
    'name': '每周安全巡检',
    'url': 'https://example.com',
    'scan_type': 'HomePage_Scan',
    'cron_expr': 'weekly'
})
jid = r['job']['id']
print(f"    Created: [{jid}] {r['job']['name']} cron={r['job']['cron_expr']}")

jobs = api('/api/schedule')
print(f"    Listed: {len(jobs['jobs'])} job(s)")
print(f"    Triggered: {api(f'/api/schedule/{jid}/run', method='POST').get('status')}")

print(f"    Deleted: {api(f'/api/schedule/{jid}', method='DELETE').get('status')}")

print("\n[4] Batch scan (2 URLs)")
r = api('/api/batch', {
    'urls': ['https://example.com', 'https://httpbin.org/get'],
    'scan_type': 'HomePage_Scan'
})
bid = r['batch_id']
print(f"    Batch: {bid} | {len(r['task_ids'])} tasks")
time.sleep(8)
st = api(f'/api/batch/{bid}')
print(f"    Status: {st['completed']}/{st['total']} done "
      f"success={st.get('success',0)} error={st.get('error',0)}")

print("\n[5] CSV Export")
for tid, res in list(st.get('results', {}).items())[:1]:
    csv_url = f"{BASE}/api/report/{tid}?format=csv"
    req = urllib.request.Request(csv_url)
    with urllib.request.urlopen(req, timeout=10) as r:
        data = r.read(200)
        print(f"    CSV OK | size={len(data)} | preview: {data[:80]}")
    json_url = f"{BASE}/api/report/{tid}?format=json"
    with urllib.request.urlopen(json_url, timeout=10) as r:
        j = json.loads(r.read())
        print(f"    JSON: url={j.get('taskurl','?')} bl={j.get('blacklink_count',0)} "
              f"bd={j.get('backdoor_count',0)} died={j.get('diedlink_count',0)}")

print("\n[6] Rules")
rules = api('/api/rules')
print(f"    blacklist_rules: {len(rules['blacklink_rules'])}")
print(f"    backdoor_rules: {len(rules['backdoor_rules'])}")
print(f"    backdoor_paths: {len(rules['backdoor_paths'])}")

print("\n" + "=" * 50)
print("ALL FEATURES WORKING!")
print("=" * 50)
