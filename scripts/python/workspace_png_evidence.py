"""Stage bounded, unchanged workspace HC PNGs; never accept visual evidence."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

VIEWS = ('records', 'schema', 'imports', 'exports')
CASES = {view: f'workspace-release-workspac-{"92e7c" if view in ("records", "schema") else "a27fb"}-ponsive-and-visually-stable-chromium-high-contrast' for view in VIEWS}
MAX_PNG_BYTES = 30 * 1024 * 1024  # Leave >1 MiB for provenance and ZIP overhead.


def stage(source: Path, output: Path, provenance: dict) -> None:
    if output.exists() or output.is_symlink():
        raise ValueError('workspace PNG output must be fresh')
    inventory = {}
    for view in VIEWS:
        names = [f'workspace-{view}-chromium-high-contrast-{kind}.png'
                 for kind in ('actual', 'expected', 'diff')]
        names.append(f'workspace-{view}-post-assert.png')
        members = []
        for name in names:
            path = source / CASES[view] / name
            if any(parent.is_symlink() for parent in (path, *path.parents)):
                raise ValueError('workspace PNG symlink rejected')
            if not path.exists():
                continue
            if not path.is_file():
                raise ValueError('workspace PNG must be a regular file')
            members.append(path)
        if sum(path.stat().st_size for path in members) > MAX_PNG_BYTES:
            raise ValueError('workspace PNG artifact exceeds bounded size')
        inventory[view] = members
    # Validate all views before writing; preserve original files on every outcome.
    for view, members in inventory.items():
        target = output / view
        target.mkdir(parents=True)
        captures = []
        for path in members:
            destination = target / path.name
            shutil.copyfile(path, destination)
            captures.append({'path': str(path.relative_to(source)),
                             'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
                             'bytes': destination.stat().st_size})
        body = {**provenance, 'view': view, 'captures': captures,
                'scope': 'Diagnostic HC PNG copies only; no visual acceptance.'}
        metadata = json.dumps(body, indent=2) + '\n'
        if len(metadata.encode()) > 65536:
            raise ValueError('workspace PNG provenance exceeds bounded size')
        (target / 'provenance.json').write_text(metadata)


def main() -> None:
    def git(*args):
        return subprocess.check_output(['git', *args], text=True, timeout=10).strip()

    stage(Path('.artifacts/workspace-124'), Path('.artifacts/workspace-png-124'), {
        'schemaVersion': 1, 'sourceCommit': git('rev-parse', 'HEAD'),
        'sourceTree': git('rev-parse', 'HEAD^{tree}'),
        'requestedHead': os.environ['WORKSPACE_REQUESTED_HEAD'],
        'runId': os.environ['GITHUB_RUN_ID'],
        'attempt': os.environ['GITHUB_RUN_ATTEMPT'],
        'workspaceOutcome': os.environ['WORKSPACE_OUTCOME'],
    })


if __name__ == '__main__':
    main()
