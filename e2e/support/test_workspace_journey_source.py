"""Narrow source guardrails, not browser/Compose execution evidence."""

import re
from pathlib import Path

SOURCE = Path(__file__).parents[1] / "tests/workspace-policy.spec.js"


def test_recovery_uses_service_only_compose_up_never_replays_setup():
    source = SOURCE.read_text()
    assert "compose('start'" not in source
    assert "compose('restart'" not in source
    assert "'--no-deps','--no-build','--no-recreate','--pull','never'" in re.sub(r"\s+", "", source)
    assert "['celery-content-worker', 'celery-beat'].includes(service)" in source


def test_notification_success_targets_exact_saved_announcement_not_implicit_status():
    source = SOURCE.read_text()
    assert "first.getByRole('status')" not in source
    assert 'div[role="status"]' in source
    assert "/^Notification preferences saved\\.$/" in source


def test_real_shared_policy_ui_covers_isolation_conflict_and_no_write_recovery():
    source = SOURCE.read_text()
    for marker in (
        "Keep editing",
        "Discard policy drafts and reload",
        "Settings categories",
        "cross-category shared-policy UI",
        "expected_version: baseline.version",
        "expect(writes).toHaveLength(4)",
    ):
        assert marker in source
    assert "await policy(owner, true, 'public_allowed');" not in source


def test_service_resume_helper_emits_only_fixed_dependency_free_commands():
    import subprocess

    # Evaluate only the pure command builder with a fake Compose function. No
    # child_process import, Docker invocation, database, or browser is involved.
    function = (
        SOURCE.read_text()
        .split("function resumeService(service) {", 1)[1]
        .split("function control(", 1)[0]
    )
    script = (
        """const assert = require('node:assert/strict');
      function compose(...args) { return args; }
      function resumeService(service) {"""
        + function
        + """
      for (const service of ['celery-content-worker', 'celery-beat']) {
        assert.deepEqual(resumeService(service), ['up', '-d', '--no-deps', '--no-build', '--no-recreate', '--pull', 'never', service]);
      }
      for (const invalid of ['workspace-fixture', 'api-migrate', 'postgres', '', 'celery-beat;echo unsafe']) {
        assert.throws(() => resumeService(invalid), /Only existing/);
      }
    """
    )
    result = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
