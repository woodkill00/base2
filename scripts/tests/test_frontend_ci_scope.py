import importlib.util
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("frontend_ci_scope", ROOT / "scripts/python/frontend_ci_scope.py")


@pytest.fixture
def policy():
    module = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(module)
    return module


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True).stdout.decode().strip()


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "test@example.invalid")
    git(tmp_path, "config", "user.name", "Test")
    git(tmp_path, "commit", "--allow-empty", "-qm", "base")
    return tmp_path


def commit(root, path, body=b"# Narrative\n"):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)
    git(root, "add", "--", path)
    git(root, "commit", "-qm", "change")
    return git(root, "rev-parse", "HEAD")


def test_narrative_only(policy, repo):
    base = git(repo, "rev-parse", "HEAD")
    head = commit(repo, "specs/114-feature/tasks.md")
    result = policy.classify(repo, base, head)
    assert result["mode"] == "narrative"
    assert result["baseCommit"] == base and result["sourceCommit"] == head
    assert result["browserTests"] == "not-run-by-policy"


@pytest.mark.parametrize("path", ["react-app/src/App.jsx", "specs/114-feature/coverage.json",
    "specs/114-feature/validate_plan.py", "AGENTS.md", "docs/runtime.md",
    ".github/workflows/ci-frontend.yml", "scripts/python/frontend_ci_scope.py",
    "specs/114-feature/x\nplan.md", "specs/114-feature/snapshots/view.png"])
def test_non_narrative_requires_full(policy, repo, path):
    base = git(repo, "rev-parse", "HEAD")
    head = commit(repo, path)
    assert policy.classify(repo, base, head)["mode"] == "full"


def test_mixed_requires_full(policy, repo):
    base = git(repo, "rev-parse", "HEAD")
    commit(repo, "specs/114-feature/plan.md")
    head = commit(repo, "package.json")
    assert policy.classify(repo, base, head)["mode"] == "full"


@pytest.mark.parametrize("change", ["delete", "rename", "executable", "symlink"])
def test_unsafe_change_modes_require_full(policy, repo, change):
    path = "specs/114-feature/tasks.md"
    base = commit(repo, path)
    target = repo / path
    if change == "delete":
        target.unlink()
    elif change == "rename":
        target.rename(target.with_name("plan.md"))
    elif change == "executable":
        target.chmod(0o755)
    else:
        target.unlink(); target.symlink_to("/etc/passwd")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "unsafe delta")
    assert policy.classify(repo, base, git(repo, "rev-parse", "HEAD"))["mode"] == "full"


@pytest.mark.parametrize("base", ["--help", "f" * 40, "0" * 40, "HEAD"])
def test_missing_invalid_history_requires_full(policy, repo, base):
    assert policy.classify(repo, base, git(repo, "rev-parse", "HEAD"))["mode"] == "full"


@pytest.mark.parametrize("body", [b"", b"\xff", b"# Missing newline", b"\x00\n"])
def test_invalid_narrative_fails(policy, repo, body):
    base = git(repo, "rev-parse", "HEAD")
    head = commit(repo, "specs/114-feature/plan.md", body)
    with pytest.raises(ValueError):
        policy.classify(repo, base, head)


def test_empty_diff_does_not_skip(policy, repo):
    head = git(repo, "rev-parse", "HEAD")
    assert policy.classify(repo, head, head)["mode"] == "full"


def test_workflow_keeps_required_job_and_base_policy():
    import yaml
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci-frontend.yml").read_text())
    frontend = workflow["jobs"]["frontend"]
    assert "if" not in frontend
    steps = frontend["steps"]
    classifier = next(step for step in steps if step.get("id") == "scope")
    assert 'git show "$BASE_COMMIT:scripts/python/frontend_ci_scope.py"' in classifier["run"]
    assert "pull_request.base.sha" in classifier["env"]["BASE_COMMIT"]
    assert "github.event.before" in classifier["env"]["BASE_COMMIT"]
    assert "pull_request.head.sha" in classifier["env"]["HEAD_COMMIT"]
    assert "mode=full" in classifier["run"]
    for step in steps[steps.index(classifier) + 1:]:
        assert "steps.scope.outputs.mode == 'full'" in step.get("if", ""), step["name"]
    assert "needs.frontend.outputs.scope == 'full'" in workflow["jobs"]["chromatic"]["if"]


def test_cli_outputs_explicit_non_execution(policy, repo, tmp_path):
    import json
    base = git(repo, "rev-parse", "HEAD")
    head = commit(repo, "specs/114-feature/tasks.md")
    output = tmp_path / "output"
    summary = tmp_path / "summary"
    result = subprocess.run(["python3", str(ROOT / "scripts/python/frontend_ci_scope.py"),
        "--root", str(repo), "--base", base, "--head", head,
        "--github-output", str(output), "--summary", str(summary)], capture_output=True, text=True)
    assert result.returncode == 0
    assert json.loads(result.stdout)["browserTests"] == "not-run-by-policy"
    assert output.read_text() == "mode=narrative\n"
    assert "not-run-by-policy" in summary.read_text()
