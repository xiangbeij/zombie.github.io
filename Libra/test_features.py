#!/usr/bin/env python3
"""Quick API endpoint tests - no long scans"""
import urllib.request
import json

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

def apiget(path):
    with urllib.request.urlopen(BASE + path, timeout=15) as r:
        return json.loads(r.read())

print("=" * 50)
print("QUICK API TESTS")
print("=" * 50)

print("\n[1] /api/health")
print("   ", api('/api/health'))

print("\n[2] /api/stats")
print("   ", api('/api/stats'))

print("\n[3] /api/tasks")
print("   Total tasks:", api('/api/tasks').get('total', 0))

print("\n[4] /api/schedule POST (create)")
r = api('/api/schedule', {
    'name': '测试定时任务',
    'url': 'https://example.com',
    'scan_type': 'HomePage_Scan',
    'cron_expr': 'hourly'
})
job_id = r['job']['id']
print("   Created:", job_id, r['job']['name'], "| cron:", r['job']['cron_expr'])

print("\n[5] /api/schedule GET (list)")
jobs = api('/api/schedule')
for j in jobs.get('jobs', []):
    print(f"   [{j['id']}] {j['name']} | {j['url']} | {j['cron_expr']} | enabled={j['enabled']}")

print("\n[6] /api/schedule PUT (toggle enabled)")
r2 = api(f'/api/schedule/{job_id}', {'enabled': False}, method='PUT')
print("   Disabled:", r2['job']['enabled'])

print("\n[7] /api/schedule DELETE")
r3 = api(f'/api/schedule/{job_id}', method='DELETE')
print("   Delete status:", r3.get('status'))

print("\n[8] /api/schedule POST again (re-create for next test)")
r = api('/api/schedule', {
    'name': '每6小时巡检',
    'url': 'https://example.com',
    'scan_type': 'HomePage_Scan',
    'cron_expr': '0 */6 * * *'
})
job_id2 = r['job']['id']
print("   Created:", job_id2, r['job']['name'], "| cron:", r['job']['cron_expr'])

print("\n[9] /api/schedule/<id>/run (trigger now)")
r4 = api(f'/api/schedule/{job_id2}/run', method='POST')
print("   Triggered:", r4.get('status'))

print("\n[10] /api/scan POST (quick single scan)")
import socket
# Use a local-ish test that responds fast
r5 = api('/api/scan', {'url': 'http://newhntest1.scuos.com', 'scan_type': 'HomePage_Scan'})
print("   Task created:", r5.get('task_id'), r5.get('message'))

print("\n[11] /api/batch POST")
r6 = api('/api/batch', {
    'urls': ['http://newhntest1.scuos.com', 'http://210.44.49.21'],
    'scan_type': 'HomePage_Scan'
})
print("   Batch:", r6.get('batch_id'), "| tasks:", len(r6.get('task_ids', [])))

print("\n[12] /api/batch/<id> GET")
st = api(f'/api/batch/{r6["batch_id"]}')
print(f"   total={st['total']} completed={st['completed']} success={st.get('success',0)} error={st.get('error',0)} running={st.get('running',0)}")

print("\n[13] /api/report/<task_id>?format=csv")
if st.get('results'):
    first_tid = list(st['results'].keys())[0]
    csv_url = f"{BASE}/api/report/{first_tid}?format=csv"
    req = urllib.request.Request(csv_url)
    with urllib.request.urlopen(req, timeout=10) as resp:
        print(f"   Status: {resp.status}  Size: {len(resp.read())} bytes")
else:
    print("   No results yet (tasks still running)")

print("\n[14] /api/rules GET")
rules = api('/api/rules')
print(f"   blacklist_rules: {len(rules.get('blacklink_rules', []))}")
print(f"   backdoor_rules: {len(rules.get('backdoor_rules', []))}")
print(f"   violativelink_rules: {len(rules.get('violativelink_rules', []))}")
print(f"   backdoor_paths: {len(rules.get('backdoor_paths', []))}")

print("\n" + "=" * 50)
print("ALL ENDPOINTS WORKING")
print("=" * 50)
