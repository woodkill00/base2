#!/usr/bin/env python3
"""Exercise staged traffic, failure halt, and rollback in disposable Docker resources."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from scripts.python.production_release import (
    ProductionReleaseController,
    approval,
    sign_release,
)

IMAGE = 'nginx@sha256:516475cc129da42866742567714ddc681e5eed7b9ee0b9e9c015e464b4221a00'
RELEASE_KEY = b'local-release-acceptance-key-material-01'
APPROVAL_KEY = b'local-owner-approval-key-material-0001'


def run(*parts: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(parts, check=check, text=True, capture_output=True, timeout=20)


class DockerAdapter:
    def __init__(self, root: Path):
        self.suffix = str(os.getpid())
        self.network = f'base2-release-{self.suffix}'
        self.proxy = f'base2-release-proxy-{self.suffix}'
        self.root = root
        self.candidates: dict[str, str] = {}
        run('docker', 'network', 'create', '--label', 'base2.owner=feature-106-local', self.network)

    def candidate_name(self, release_id: str) -> str:
        return f'base2-{release_id}-{self.suffix}'.lower()

    def execute(self, action: str, release: dict, environment: str) -> dict:
        name = self.candidate_name(release['releaseId'])
        if action == 'stage':
            if run('docker', 'inspect', name, check=False).returncode != 0:
                run(
                    'docker', 'run', '-d', '--name', name, '--network', self.network,
                    '--label', 'base2.owner=feature-106-local', release['images']['web'],
                )
            self.candidates[release['releaseId']] = name
        elif action == 'canary':
            if run('docker', 'inspect', name, check=False).returncode != 0:
                return self.receipt(action, release, environment, 'failed')
        elif action == 'promote':
            run('docker', 'rm', '-f', self.proxy, check=False)
            config = self.root / 'nginx.conf'
            config.write_text(
                'events {}\nhttp { server { listen 80; location / { proxy_pass http://'
                f'{name}:80; }} }} }}\n',
                encoding='utf-8',
            )
            run(
                'docker', 'run', '-d', '--name', self.proxy, '--network', self.network,
                '--label', 'base2.owner=feature-106-local', '-v',
                f'{config}:/etc/nginx/nginx.conf:ro', IMAGE,
            )
        elif action == 'rollback':
            run('docker', 'rm', '-f', name, check=False)
        return self.receipt(action, release, environment, 'succeeded')

    @staticmethod
    def receipt(action: str, release: dict, environment: str, status: str) -> dict:
        return {
            'action': action,
            'releaseId': release['releaseId'],
            'environment': environment,
            'status': status,
        }

    def healthy(self, action: str) -> bool:
        target = self.proxy if action == 'promote' else next(reversed(self.candidates.values()))
        for _ in range(30):
            if run(
                'docker', 'exec', target, 'wget', '-qO-', 'http://127.0.0.1/', check=False
            ).returncode == 0:
                return True
            time.sleep(0.1)
        return False

    def cleanup(self) -> None:
        run('docker', 'rm', '-f', self.proxy, *self.candidates.values(), check=False)
        run('docker', 'network', 'rm', self.network, check=False)


def make_release(number: int, now: datetime) -> dict:
    digit = str(number)
    return sign_release(
        {
            'schemaVersion': 2,
            'releaseId': f'release-local-{number:04d}',
            'sourceCommit': digit * 40,
            'sourceClean': True,
            'images': {'web': IMAGE},
            'migrationsDigest': digit * 64,
            'configurationSchemaVersion': 1,
            'configurationDigest': digit * 64,
            'sbomDigest': digit * 64,
            'provenanceDigest': digit * 64,
            'createdAt': now.isoformat(),
        },
        key=RELEASE_KEY,
    )


def permit(action: str, release: dict, now: datetime) -> dict:
    return approval(
        approval_id=f'approval-{action}-{release["releaseId"]}',
        action=action,
        release_id=release['releaseId'],
        environment='staging',
        expires_at=(now + timedelta(minutes=10)).isoformat(),
        key=APPROVAL_KEY,
    )


def main() -> int:
    now = datetime.now(UTC)
    with tempfile.TemporaryDirectory(prefix='base2-release-') as temporary:
        root = Path(temporary)
        adapter = DockerAdapter(root)
        controller = ProductionReleaseController(
            root / 'journal.json', release_key=RELEASE_KEY, approval_key=APPROVAL_KEY
        )
        try:
            first = make_release(1, now)
            for action in ('prepare', 'stage', 'canary', 'promote'):
                result = controller.transition(
                    action=action,
                    release=first,
                    environment='staging',
                    owner_approval=permit(action, first, now),
                    now=now,
                    health=adapter.healthy,
                    execute=adapter.execute,
                )
                if result['status'] == 'halted':
                    raise RuntimeError(f'local_release_{action}_failed')
            second = make_release(2, now)
            for action in ('prepare', 'stage'):
                controller.transition(
                    action=action,
                    release=second,
                    environment='staging',
                    owner_approval=permit(action, second, now),
                    now=now,
                    health=adapter.healthy,
                    execute=adapter.execute,
                )
            halted = controller.transition(
                action='canary', release=second, environment='staging',
                owner_approval=permit('canary', second, now), now=now,
                health=lambda action: False, execute=adapter.execute,
            )
            rolled = controller.transition(
                action='rollback', release=second, environment='staging',
                owner_approval=permit('rollback', second, now), now=now,
                execute=adapter.execute,
            )
            status = controller.status()
            if (
                halted['status'] != 'halted'
                or rolled['status'] != 'rolled-back'
                or status['current'] != first['releaseId']
                or not adapter.healthy('promote')
            ):
                raise RuntimeError('local_release_rollback_failed')
            print(json.dumps({'status': 'passed', 'current': status['current']}, sort_keys=True))
            return 0
        finally:
            adapter.cleanup()


if __name__ == '__main__':
    raise SystemExit(main())
