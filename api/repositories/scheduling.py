from __future__ import annotations
from uuid import UUID, uuid4
from psycopg2.errors import RaiseException
from api.db import db_conn


class SchedulingRepository:
    def list_events(self, *, site_id: str):
        with db_conn(tenant_id=site_id) as conn, conn.cursor() as cur:
            cur.execute(
                """SELECT id,slug,title,starts_at,ends_at,timezone_name,capacity,booking_open
                           FROM scheduling_event WHERE site_id=%s AND ends_at>NOW()
                           ORDER BY starts_at,id LIMIT 100""",
                (site_id,),
            )
            return [
                {
                    'id': r[0],
                    'slug': r[1],
                    'title': r[2],
                    'startsAt': r[3],
                    'endsAt': r[4],
                    'timezone': r[5],
                    'capacity': r[6],
                    'bookingOpen': r[7],
                }
                for r in cur.fetchall()
            ]

    def reserve(self, *, site_id: str, event_id: UUID, attendee_ref: str, seats: int):
        # A fixed database capability owns locks, tenant scope and capacity.
        # Runtime has no direct event/booking mutation privileges.
        with db_conn(tenant_id=site_id) as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        'SELECT booking_id,booking_status,replayed '
                        'FROM public.base2_reserve_booking(%s,%s,%s,%s)',
                        (str(uuid4()), str(event_id), attendee_ref, seats),
                    )
                    row = cur.fetchone()
                    if row is None:
                        raise RuntimeError('booking_result_missing')
                conn.commit()
                return {'id': row[0], 'status': row[1], 'replayed': row[2]}
            except RaiseException as exc:
                conn.rollback()
                code = exc.diag.message_primary
                if code in {
                    'booking_invalid',
                    'event_not_found',
                    'booking_closed',
                    'booking_replay_conflict',
                    'capacity_exceeded',
                }:
                    raise ValueError(code) from None
                raise RuntimeError('booking_database_rejected') from None
            except Exception:
                conn.rollback()
                raise
