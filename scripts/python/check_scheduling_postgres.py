"""Optional booking lifecycle using the real restricted API role and disposable DB."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import uuid4

import psycopg2
from psycopg2 import errors

from api import db
from api.repositories.scheduling import SchedulingRepository


def check(owner, pool_context, user, password):
    tenant = "booking-acceptance"
    other = "booking-other"
    active, expired, closed, foreign, race = (uuid4() for _ in range(5))
    now = datetime.now(UTC)
    ids = [str(value) for value in (active, expired, closed, foreign, race)]
    with owner, owner.cursor() as cursor:
        for event_id, site, start, end, is_open in (
            (active, tenant, now, now + timedelta(hours=1), True),
            (expired, tenant, now - timedelta(hours=2), now - timedelta(hours=1), True),
            (closed, tenant, now, now + timedelta(hours=1), False),
            (foreign, other, now, now + timedelta(hours=1), True),
        ):
            cursor.execute(
                """INSERT INTO scheduling_event
                (id,site_id,slug,title,starts_at,ends_at,timezone_name,capacity,
                 booking_open,created_at,updated_at)
                VALUES (%s,%s,%s,'Fixture',%s,%s,'UTC',1,%s,NOW(),NOW())""",
                (str(event_id), site, str(event_id), start, end, is_open),
            )
    try:
        with pool_context(user, password):
            repo = SchedulingRepository()
            listed = {str(event["id"]) for event in repo.list_events(site_id=tenant)}
            assert listed == {str(active), str(closed)}, "event_visibility_failed"
            first = repo.reserve(site_id=tenant, event_id=active, attendee_ref="first", seats=1)
            replay = repo.reserve(site_id=tenant, event_id=active, attendee_ref="first", seats=1)
            assert replay["replayed"] and replay["id"] == first["id"], "booking_replay_failed"
            for event_id, attendee, seats, expected in (
                (active, "second", 1, "capacity_exceeded"),
                (active, "first", 2, "booking_replay_conflict"),
                (expired, "first", 1, "booking_closed"),
                (closed, "first", 1, "booking_closed"),
                (foreign, "first", 1, "event_not_found"),
            ):
                try:
                    repo.reserve(
                        site_id=tenant, event_id=event_id, attendee_ref=attendee, seats=seats
                    )
                except ValueError as exc:
                    assert str(exc) == expected, "unexpected_booking_rejection"
                else:
                    raise AssertionError("unsafe_booking_accepted")
            # Failed transactions must not poison subsequent pool checkouts.
            assert len(repo.list_events(site_id=tenant)) == 2
            with db.db_conn() as conn, conn.cursor() as cursor:
                cursor.execute("SELECT id FROM scheduling_event")
                assert cursor.fetchall() == [], "tenant_context_leaked"
            for sql in (
                "UPDATE scheduling_event SET capacity=999",
                "DELETE FROM scheduling_booking",
                "SELECT * FROM scheduling_booking",
            ):
                try:
                    with db.db_conn(tenant_id=tenant) as conn, conn.cursor() as cursor:
                        cursor.execute(sql)
                except errors.InsufficientPrivilege:
                    pass
                else:
                    raise AssertionError("direct_booking_access_allowed")
        with owner, owner.cursor() as cursor:
            cursor.execute(
                """INSERT INTO scheduling_event
                (id,site_id,slug,title,starts_at,ends_at,timezone_name,capacity,
                 booking_open,created_at,updated_at)
                VALUES (%s,%s,%s,'Race',NOW(),NOW()+INTERVAL '1 hour','UTC',1,true,NOW(),NOW())""",
                (str(race), tenant, str(race)),
            )
        barrier = Barrier(2, timeout=5)

        def contend(attendee):
            # Independent restricted connections; no global pool monkeypatch in threads.
            with closing(
                psycopg2.connect(
                    host=owner.info.host,
                    port=owner.info.port,
                    dbname=owner.info.dbname,
                    user=user,
                    password=password,
                    connect_timeout=3,
                    options="-c statement_timeout=5000 -c lock_timeout=4000",
                )
            ) as connection:
                try:
                    with connection, connection.cursor() as cursor:
                        cursor.execute("SELECT set_config('app.tenant_id',%s,true)", (tenant,))
                        barrier.wait()
                        cursor.execute(
                            "SELECT * FROM public.base2_reserve_booking(%s,%s,%s,1)",
                            (str(uuid4()), str(race), attendee),
                        )
                        assert cursor.fetchone()[1:] == ("confirmed", False)
                    return "confirmed"
                except errors.RaiseException as exc:
                    assert exc.diag.message_primary == "capacity_exceeded"
                    return "capacity_exceeded"

        with ThreadPoolExecutor(max_workers=2) as workers:
            outcomes = list(workers.map(contend, ("race-one", "race-two")))
        assert sorted(outcomes) == ["capacity_exceeded", "confirmed"], "capacity_race_failed"
        with owner, owner.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*),SUM(seats) FROM scheduling_booking WHERE event_id=%s", (str(race),)
            )
            assert cursor.fetchone() == (1, 1), "capacity_race_overbooked"
    finally:
        with owner, owner.cursor() as cursor:
            cursor.execute(
                "DELETE FROM scheduling_booking WHERE event_id = ANY(%s::uuid[])", (ids,)
            )
            cursor.execute("DELETE FROM scheduling_event WHERE id = ANY(%s::uuid[])", (ids,))
    print("Scheduling restricted-role lifecycle acceptance: PASS")
