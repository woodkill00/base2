from pathlib import Path

from digital_ocean.scripts.python.scan_artifact_secrets import CHUNK_BYTES, main, scan_tree


def test_recursive_artifact_scan_accepts_sanitized_tree(tmp_path: Path):
    env = tmp_path / "source.env"
    env.write_text("DB_PASSWORD=very-private-canary\nPUBLIC_NAME=demo\n", encoding="utf-8")
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    (artifacts / "safe.txt").write_text("DB_PASSWORD=[REDACTED]\n", encoding="utf-8")
    assert scan_tree(artifacts, env) == []


def test_recursive_artifact_scan_rejects_nested_secret_and_private_key(tmp_path: Path):
    env = tmp_path / "source.env"
    env.write_text("JWT_SECRET=unique-secret-canary\n", encoding="utf-8")
    artifacts = tmp_path / "artifacts"
    nested = artifacts / "logs" / "build"
    nested.mkdir(parents=True)
    (nested / "compose.yml").write_text("value: unique-secret-canary\n", encoding="utf-8")
    (nested / "key.txt").write_text("-----BEGIN PRIVATE KEY-----\n", encoding="utf-8")
    assert scan_tree(artifacts, env) == ["logs/build/compose.yml", "logs/build/key.txt"]


def test_recursive_artifact_scan_does_not_skip_oversized_files(tmp_path: Path):
    env = tmp_path / "source.env"
    env.write_text("JWT_SECRET=oversized-secret-canary\n", encoding="utf-8")
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    payload = artifacts / "oversized.log"
    with payload.open("wb") as handle:
        handle.write(b"x" * (17 * 1024 * 1024))
        handle.write(b"oversized-secret-canary")
    assert scan_tree(artifacts, env) == ["oversized.log"]


def test_recursive_artifact_scan_matches_across_chunk_boundary(tmp_path: Path):
    env = tmp_path / "source.env"
    env.write_text("API_TOKEN=boundary-secret-canary\n", encoding="utf-8")
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    payload = artifacts / "boundary.log"
    prefix = b"x" * (CHUNK_BYTES - len(b"boundary-secret-") + 3)
    payload.write_bytes(prefix + b"boundary-secret-canary")
    assert scan_tree(artifacts, env) == ["boundary.log"]


def test_recursive_artifact_scan_ignores_non_secrets_and_rejects_symlinks(tmp_path: Path):
    env = tmp_path / "source.env"
    env.write_text(
        "\n# comment\nPUBLIC_NAME=demo\nSHORT_TOKEN=tiny\n"
        "REFERENCE_TOKEN=${TOKEN_FROM_VAULT}\nMALFORMED\n",
        encoding="utf-8",
    )
    artifacts = tmp_path / "artifacts"
    nested = artifacts / "nested"
    nested.mkdir(parents=True)
    target = tmp_path / "outside.txt"
    target.write_text("safe", encoding="utf-8")
    (nested / "outside-link").symlink_to(target)

    assert scan_tree(artifacts, env) == ["nested/outside-link"]


def test_artifact_scan_cli_reports_pass_and_rejection(monkeypatch, capsys, tmp_path: Path):
    env = tmp_path / "source.env"
    env.write_text("API_TOKEN=command-line-secret\n", encoding="utf-8")
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    monkeypatch.setattr("sys.argv", ["scan", "--root", str(artifacts), "--env-file", str(env)])
    assert main() == 0
    assert '"status": "passed"' in capsys.readouterr().out

    (artifacts / "leak.txt").write_text("command-line-secret", encoding="utf-8")
    assert main() == 2
    output = capsys.readouterr().out
    assert '"status": "rejected"' in output
    assert '"findingCount": 1' in output
    assert '"leak.txt"' in output
