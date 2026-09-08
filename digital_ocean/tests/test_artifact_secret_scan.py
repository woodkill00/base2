from pathlib import Path

from digital_ocean.scripts.python.scan_artifact_secrets import scan_tree


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
