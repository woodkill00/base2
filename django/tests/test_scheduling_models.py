from datetime import UTC, datetime, timedelta

import pytest
from django.core.exceptions import ValidationError

from scheduling.models import Event


@pytest.mark.django_db
def test_timezone_capacity_tenant_and_replay_contract():
    event = Event.objects.create(
        site_id="tenant-one",
        slug="launch",
        title="Launch",
        starts_at=datetime.now(UTC) + timedelta(days=1),
        ends_at=datetime.now(UTC) + timedelta(days=1, hours=1),
        timezone_name="Europe/Berlin",
        capacity=2,
        booking_open=True,
    )
    event.full_clean()
    first, created = Event.reserve(
        event_id=event.id, site_id="tenant-one", attendee_ref="user-one", seats=1
    )
    assert created and first.seats == 1
    replay, created = Event.reserve(
        event_id=event.id, site_id="tenant-one", attendee_ref="user-one", seats=1
    )
    assert not created and replay.id == first.id
    Event.reserve(event_id=event.id, site_id="tenant-one", attendee_ref="user-two", seats=1)
    replay, created = Event.reserve(
        event_id=event.id, site_id="tenant-one", attendee_ref="user-one", seats=1
    )
    assert not created and replay.id == first.id
    with pytest.raises(ValidationError, match="booking_replay_conflict"):
        Event.reserve(event_id=event.id, site_id="tenant-one", attendee_ref="user-one", seats=2)
    with pytest.raises(ValidationError, match="capacity_exceeded"):
        Event.reserve(event_id=event.id, site_id="tenant-one", attendee_ref="user-three", seats=1)
    with pytest.raises(Event.DoesNotExist):
        Event.reserve(event_id=event.id, site_id="tenant-two", attendee_ref="hostile", seats=1)


@pytest.mark.django_db
def test_invalid_timezone_and_naive_times_fail_closed():
    event = Event(
        site_id="tenant-one",
        slug="bad",
        title="Bad",
        starts_at=datetime.now(),
        ends_at=datetime.now() + timedelta(hours=1),
        timezone_name="Not/AZone",
        capacity=1,
    )
    with pytest.raises(ValidationError):
        event.full_clean()


def test_live_race_cli_preserves_setup_assertions_and_result():
    """Inspect the live proof contract without running its database/thread workload."""
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    caller = ast.parse((root / "scripts/python/run_scheduling_postgres_acceptance.py").read_text())
    direct_calls = [
        node
        for node in ast.walk(caller)
        if isinstance(node, ast.Call)
        and ast.unparse(node.func) == "subprocess.run"
        and node.args
        and ast.unparse(node.args[0]) == "[*base, 'tests/live_scheduling_race.py']"
    ]
    assert len(direct_calls) == 1
    assert any(k.arg == "check" and k.value.value is True for k in direct_calls[0].keywords)
    base = next(
        node.value
        for node in ast.walk(caller)
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "base" for target in node.targets)
    )
    assert [ast.literal_eval(item) for item in base.elts[-3:]] == [
        "--entrypoint",
        "python",
        "base2-f093-1115-django:latest",
    ]

    script = ast.parse((root / "django/tests/live_scheduling_race.py").read_text())
    main, guard = script.body
    assert isinstance(main, ast.FunctionDef) and main.name == "main"
    assert ast.dump(guard) == ast.dump(ast.parse('if __name__ == "__main__": main()').body[0])
    statements = [ast.unparse(node) for node in main.body]
    env_index = statements.index(
        "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings.base')"
    )
    django_index = statements.index("import django")
    setup_index = statements.index("django.setup()")
    models_index = statements.index("from scheduling.models import Booking, Event")
    assert env_index < django_index < setup_index < models_index
    assert statements[-3:] == [
        "assert sorted(outcomes) == ['capacity_exceeded', 'confirmed'], outcomes",
        "assert Booking.objects.filter(event=event, status='confirmed').count() == 1",
        'print(\'{"capacityRace":"passed","confirmed":1,"rejected":1}\')',
    ]
