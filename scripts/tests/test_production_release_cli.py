import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from scripts.python.production_release import (
    approval,
    health_receipt,
    operation_receipt,
    sign_release,
)
from scripts.python.production_release_cli import main

RELEASE_KEY = b'release-cli-key-material-000000000001'
APPROVAL_KEY = b'approval-cli-key-material-00000000001'
OPERATION_KEY = b'operation-cli-key-material-0000000001'
HEALTH_KEY = b'health-cli-key-material-0000000000001'


def write(path: Path, value) -> Path:
    path.write_text(json.dumps(value) if isinstance(value, dict) else value, encoding='utf-8')
    path.chmod(0o600)
    return path


def candidate(now):
    return sign_release(
        {
            'schemaVersion': 2,
            'releaseId': 'release-cli-0001',
            'sourceCommit': 'a' * 40,
            'sourceClean': True,
            'images': {'web': f'registry.example/base2@sha256:{"b" * 64}'},
            'migrationsDigest': 'c' * 64,
            'configurationSchemaVersion': 1,
            'configurationDigest': 'd' * 64,
            'sbomDigest': 'e' * 64,
            'provenanceDigest': 'f' * 64,
            'createdAt': now.isoformat(),
        },
        key=RELEASE_KEY,
    )


def test_cli_prepares_then_consumes_exact_executor_receipt(tmp_path, capsys):
    now = datetime.now(UTC)
    item = candidate(now)
    journal = tmp_path / 'journal.json'
    release_path = write(tmp_path / 'release.json', item)
    release_key = write(tmp_path / 'release.key', RELEASE_KEY.decode())
    approval_key = write(tmp_path / 'approval.key', APPROVAL_KEY.decode())
    operation_key = write(tmp_path / 'operation.key', OPERATION_KEY.decode())
    health_key = write(tmp_path / 'health.key', HEALTH_KEY.decode())

    def permit(action):
        return write(
            tmp_path / f'{action}.json',
            approval(
                approval_id=f'approval-{action}-cli',
                action=action,
                release_id=item['releaseId'],
                environment='staging',
                expires_at=(now + timedelta(minutes=10)).isoformat(),
                key=APPROVAL_KEY,
            ),
        )

    common = [
        '--journal', str(journal), '--release-key-file', str(release_key),
        '--approval-key-file', str(approval_key), '--release', str(release_path),
        '--environment', 'staging',
    ]
    assert main(['prepare', *common, '--approval', str(permit('prepare'))]) == 0
    receipt = write(
        tmp_path / 'operation.json',
        operation_receipt(
            operation_id='operation-stage-cli',
            action='stage',
            release_id=item['releaseId'],
            environment='staging',
            status='succeeded',
            observed_at=now,
            key=OPERATION_KEY,
        ),
    )
    health = write(
        tmp_path / 'health.json',
        health_receipt(
            action='stage',
            release_id=item['releaseId'],
            environment='staging',
            healthy=True,
            observed_at=now,
            key=HEALTH_KEY,
        ),
    )
    assert main(
        [
            'stage', *common, '--approval', str(permit('stage')),
            '--operation-receipt', str(receipt), '--operation-key-file', str(operation_key),
            '--health-receipt', str(health), '--health-key-file', str(health_key),
        ]
    ) == 0
    assert '"status":"staged"' in capsys.readouterr().out


def test_cli_rejects_world_readable_secret_file(tmp_path, capsys):
    key = write(tmp_path / 'key', RELEASE_KEY.decode())
    key.chmod(0o644)
    code = main(
        [
            'status', '--journal', str(tmp_path / 'journal.json'),
            '--release-key-file', str(key), '--approval-key-file', str(key),
        ]
    )
    assert code == 2
    assert 'key_file_unsafe' in capsys.readouterr().out
