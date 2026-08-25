#!/usr/bin/env python3
import os,secrets,subprocess,time
from pathlib import Path
root=Path(__file__).resolve().parents[2]; name=f'base2-scheduling-{os.getpid()}'; password=secrets.token_urlsafe(32); started=False
try:
    subprocess.run(['docker','run','-d','--rm','--name',name,'--label','base2.owner=feature-093-scheduling','-e',f'POSTGRES_PASSWORD={password}','-e','POSTGRES_USER=base2','-e','POSTGRES_DB=base2','postgres:16-alpine'],check=True,stdout=subprocess.DEVNULL); started=True
    for _ in range(40):
        if subprocess.run(['docker','exec',name,'pg_isready','-U','base2','-d','base2'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0: break
        time.sleep(.25)
    else: raise RuntimeError('postgres_not_ready')
    base=['docker','run','--rm','--network',f'container:{name}','--read-only','--tmpfs','/tmp:rw,noexec,nosuid,size=64m','-v',f'{root}:/workspace:ro','-w','/workspace/django','-e','PYTHONPATH=/workspace/django','-e','DJANGO_SETTINGS_MODULE=project.settings.base','-e','DB_HOST=127.0.0.1','-e','DB_PORT=5432','-e','DB_NAME=base2','-e','DB_USER=base2','-e',f'DB_PASSWORD={password}','--entrypoint','python','base2-f093-1115-django:latest']
    subprocess.run([*base,'manage.py','migrate','--noinput'],check=True,stdout=subprocess.DEVNULL)
    subprocess.run([*base,'tests/live_scheduling_race.py'],check=True)
finally:
    if started: subprocess.run(['docker','rm','-f',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
