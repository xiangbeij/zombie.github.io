#!/usr/bin/env python3
# _*_ coding:utf-8 _*_

import sys, os, json
# Ensure /opt/Orion is in module search path
if '/opt/Orion' not in sys.path:
    sys.path.insert(0, '/opt/Orion')
if '/app' not in sys.path:
    sys.path.insert(0, '/app')  # fallback for Docker

from Framework.Orion_Console import Console


if __name__ == '__main__':
    result = Console()
    if result:
        print(json.dumps(result, ensure_ascii=False))