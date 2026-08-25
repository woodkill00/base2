from __future__ import annotations
from uuid import UUID, uuid4
from api.db import db_conn


class SchedulingRepository:
    def list_events(self, *, site_id: str):
        with db_conn(tenant_id=site_id) as conn, conn.cursor() as cur:
            cur.execute("""SELECT id,slug,title,starts_at,ends_at,timezone_name,capacity,booking_open
                           FROM scheduling_event WHERE site_id=%s AND ends_at>NOW()
                           ORDER BY starts_at,id LIMIT 100""", (site_id,))
            return [{'id':r[0],'slug':r[1],'title':r[2],'startsAt':r[3],'endsAt':r[4],
                     'timezone':r[5],'capacity':r[6],'bookingOpen':r[7]} for r in cur.fetchall()]

    def reserve(self, *, site_id: str, event_id: UUID, attendee_ref: str, seats: int):
        booking_id = uuid4()
        with db_conn(tenant_id=site_id) as conn:
            conn.autocommit = False
            try:
                with conn.cursor() as cur:
                    cur.execute("""SELECT capacity,booking_open,ends_at FROM scheduling_event
                                   WHERE id=%s AND site_id=%s FOR UPDATE""", (str(event_id),site_id))
                    event = cur.fetchone()
                    if not event: raise ValueError('event_not_found')
                    if not event[1]: raise ValueError('booking_closed')
                    cur.execute("SELECT id,seats,status FROM scheduling_booking WHERE event_id=%s AND attendee_ref=%s", (str(event_id),attendee_ref))
                    existing = cur.fetchone()
                    if existing:
                        if existing[1] != seats or existing[2] != 'confirmed': raise ValueError('booking_replay_conflict')
                        conn.rollback(); return {'id':existing[0],'status':'confirmed','replayed':True}
                    cur.execute("SELECT COALESCE(SUM(seats),0) FROM scheduling_booking WHERE event_id=%s AND status='confirmed'", (str(event_id),))
                    if cur.fetchone()[0] + seats > event[0]: raise ValueError('capacity_exceeded')
                    cur.execute("""INSERT INTO scheduling_booking(id,site_id,event_id,attendee_ref,seats,status,created_at,updated_at)
                                   VALUES (%s,%s,%s,%s,%s,'confirmed',NOW(),NOW())""",
                                (str(booking_id),site_id,str(event_id),attendee_ref,seats))
                conn.commit(); return {'id':booking_id,'status':'confirmed','replayed':False}
            except Exception:
                conn.rollback(); raise
