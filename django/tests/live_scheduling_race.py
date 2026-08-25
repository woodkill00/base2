import os, threading
from datetime import UTC, datetime, timedelta
os.environ.setdefault('DJANGO_SETTINGS_MODULE','project.settings.base')
import django
django.setup()
from django.db import close_old_connections
from django.core.exceptions import ValidationError
from scheduling.models import Event, Booking

event=Event.objects.create(site_id='tenant-one',slug='race',title='Race',starts_at=datetime.now(UTC)+timedelta(days=1),ends_at=datetime.now(UTC)+timedelta(days=1,hours=1),timezone_name='UTC',capacity=1,booking_open=True)
barrier=threading.Barrier(2); outcomes: list[str]=[]
def reserve(ref):
    close_old_connections(); barrier.wait()
    try:
        Event.reserve(event_id=event.id,site_id='tenant-one',attendee_ref=ref,seats=1); outcomes.append('confirmed')
    except ValidationError as exc:
        outcomes.append(exc.messages[0])
    finally: close_old_connections()
threads=[threading.Thread(target=reserve,args=(f'user-{n}',)) for n in (1,2)]
for thread in threads: thread.start()
for thread in threads: thread.join()
assert sorted(outcomes)==['capacity_exceeded','confirmed'],outcomes
assert Booking.objects.filter(event=event,status='confirmed').count()==1
print('{"capacityRace":"passed","confirmed":1,"rejected":1}')
