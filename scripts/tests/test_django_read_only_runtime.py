from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def test_django_disables_gunicorn_control_socket_on_read_only_root() -> None:
    compose = (ROOT / "development.docker.yml").read_text(encoding="utf-8")
    match = re.search(r"(?ms)^  django:\n(.*?)(?=^  [A-Za-z0-9_-]+:\n|\Z)", compose)
    assert match is not None
    django = match.group(1)
    entrypoint = (ROOT / "django" / "entrypoint.sh").read_text(encoding="utf-8")

    assert "\n    read_only: true\n" in django
    assert "\n      - /tmp\n" in django
    assert "\n      - /var/tmp\n" in django
    assert "--no-control-socket" in entrypoint
    assert "--control-socket " not in entrypoint
