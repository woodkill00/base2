"""Grant reservation capability, never general booking/event mutation."""

import importlib
from django.db import migrations

SIGNATURE = 'public.base2_reserve_booking(uuid,uuid,text,integer)'
SQL = r"""
CREATE FUNCTION public.base2_reserve_booking(p_id uuid, p_event uuid, p_attendee text, p_seats integer)
RETURNS TABLE(booking_id uuid, booking_status text, replayed boolean)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
DECLARE
    tenant text := current_setting('app.tenant_id', true);
    ev public.scheduling_event%ROWTYPE;
    prior public.scheduling_booking%ROWTYPE;
    used bigint;
BEGIN
    IF tenant IS NULL OR tenant !~ '^[a-z][a-z0-9-]{2,62}$'
       OR p_id IS NULL OR p_event IS NULL OR p_attendee IS NULL
       OR length(p_attendee) NOT BETWEEN 1 AND 128
       OR p_seats IS NULL OR p_seats NOT BETWEEN 1 AND 20 THEN
        RAISE EXCEPTION 'booking_invalid';
    END IF;
    SELECT * INTO ev FROM public.scheduling_event
      WHERE id = p_event AND site_id = tenant FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'event_not_found'; END IF;
    IF NOT ev.booking_open OR ev.ends_at <= clock_timestamp() THEN
        RAISE EXCEPTION 'booking_closed';
    END IF;
    SELECT * INTO prior FROM public.scheduling_booking
      WHERE event_id = p_event AND attendee_ref = p_attendee;
    IF FOUND THEN
        IF prior.site_id <> tenant OR prior.seats <> p_seats OR prior.status <> 'confirmed' THEN
            RAISE EXCEPTION 'booking_replay_conflict';
        END IF;
        RETURN QUERY SELECT prior.id, 'confirmed'::text, true;
        RETURN;
    END IF;
    SELECT COALESCE(SUM(seats), 0) INTO used FROM public.scheduling_booking
      WHERE event_id = p_event AND status = 'confirmed';
    IF used + p_seats > ev.capacity THEN RAISE EXCEPTION 'capacity_exceeded'; END IF;
    INSERT INTO public.scheduling_booking
      (id, site_id, event_id, attendee_ref, seats, status, created_at, updated_at)
      VALUES(p_id, tenant, p_event, p_attendee, p_seats, 'confirmed', NOW(), NOW());
    RETURN QUERY SELECT p_id, 'confirmed'::text, false;
END;
$$;
"""


def role(editor):
    helper = importlib.import_module('sitecontent.migrations.0034_public_content_runtime_scope')
    return helper.role_name(editor)


def configure(apps, editor):
    if editor.connection.vendor != 'postgresql':
        return
    quoted = role(editor)
    # PL/pgSQL %ROWTYPE is not a driver placeholder.
    editor.execute(SQL, params=None)
    editor.execute(f'REVOKE ALL ON FUNCTION {SIGNATURE} FROM PUBLIC')
    editor.execute(f'GRANT EXECUTE ON FUNCTION {SIGNATURE} TO {quoted}')
    editor.execute('ALTER TABLE public.scheduling_event ENABLE ROW LEVEL SECURITY')
    editor.execute(f"CREATE POLICY booking_event_read ON public.scheduling_event FOR SELECT TO {quoted} "
                   "USING (site_id=current_setting('app.tenant_id',true))")
    editor.execute(f'GRANT SELECT ON public.scheduling_event TO {quoted}')


def reverse(apps, editor):
    if editor.connection.vendor != 'postgresql':
        return
    quoted = role(editor)
    editor.execute(f'REVOKE SELECT ON public.scheduling_event FROM {quoted}')
    editor.execute('DROP POLICY booking_event_read ON public.scheduling_event')
    editor.execute(f'DROP FUNCTION {SIGNATURE}')
    # Leave RLS enabled (deny by default); do not weaken unrelated future policies.


class Migration(migrations.Migration):
    dependencies = [('sitecontent', '0034_public_content_runtime_scope'),
                    ('scheduling', '0001_initial')]
    operations = [migrations.RunPython(configure, reverse)]
