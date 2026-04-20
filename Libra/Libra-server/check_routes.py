import sys
sys.path.insert(0, '/opt/Libra/Libra-server')
from libra_assets import app
for rule in app.url_map.iter_rules():
    print(str(rule))
