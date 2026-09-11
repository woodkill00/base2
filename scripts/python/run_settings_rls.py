"""Send the exact repository/drill source into a read-only local API container."""
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[2]
payload = {'source': (root / 'api/repositories/settings.py').read_text(),
           'drill': (root / 'scripts/python/check_settings_rls.py').read_text()}
code = "import json,sys; from api.repositories import settings; p=json.load(sys.stdin); exec(compile(p['source'],'settings.py','exec'),settings.__dict__); exec(compile(p['drill'],'rls-drill.py','exec'))"
result = subprocess.run(['docker','exec','-i','base2-local_api','python','-c',code],
                        input=json.dumps(payload), text=True, capture_output=True, timeout=45)
if result.returncode:
    print('settings_runtime_drill_failed (no credentials or DB parameters emitted)')
    import re
    print('\n'.join(line for line in result.stderr.splitlines() if re.match(r'\s*File .*line \d+', line)))
    print('exception=' + result.stderr.strip().splitlines()[-1].split(':', 1)[0])
else:
    print(result.stdout.strip())
raise SystemExit(result.returncode)
