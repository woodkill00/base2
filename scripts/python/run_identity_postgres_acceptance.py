#!/usr/bin/env python3
"""Run identity acceptance beside ephemeral PostgreSQL on its private network."""
import os, secrets, subprocess, time
from pathlib import Path

def main():
    root = Path(__file__).resolve().parents[2]
    name = f'base2-identity-acceptance-{os.getpid()}'
    image = os.getenv('IDENTITY_ACCEPTANCE_API_IMAGE', 'base2-f093-1115-api:latest')
    password, started = secrets.token_urlsafe(32), False
    try:
        subprocess.run(['docker','image','inspect',image], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(['docker','run','--detach','--rm','--name',name,'--label','base2.owner=feature-093-identity-acceptance','-e',f'POSTGRES_PASSWORD={password}','-e','POSTGRES_USER=base2','-e','POSTGRES_DB=base2','postgres:16-alpine'], check=True, stdout=subprocess.DEVNULL)
        started = True
        for _ in range(40):
            ready = subprocess.run(['docker','exec',name,'pg_isready','-U','base2','-d','base2'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            if ready.returncode == 0: break
            time.sleep(.25)
        else: raise RuntimeError('postgres_acceptance:not_ready')
        subprocess.run(['docker','run','--rm','--network',f'container:{name}','--read-only','--tmpfs','/tmp:rw,noexec,nosuid,size=64m','--volume',f'{root}:/workspace:ro','--workdir','/workspace','-e','PYTHONPATH=/workspace','-e','DB_HOST=127.0.0.1','-e','DB_PORT=5432','-e','DB_NAME=base2','-e','DB_USER=base2','-e',f'DB_PASSWORD={password}','-e','PROJECT_NAME=base2-acceptance',image,'python','scripts/python/run_identity_postgres_checks.py'], check=True)
    finally:
        if started: subprocess.run(['docker','rm','--force',name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)

if __name__ == '__main__': main()
