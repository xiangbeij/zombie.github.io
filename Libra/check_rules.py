#!/usr/bin/env python3
"""Check /api/rules 500 error"""
import urllib.request, json

BASE = 'http://210.44.49.21:5189'

def get(path):
    req = urllib.request.Request(BASE + path)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return 200, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

code, body = get('/api/rules')
print(f"Status: {code}")
print(f"Body: {body}")
