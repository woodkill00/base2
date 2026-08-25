from datetime import UTC, datetime, timedelta

import pytest
from django.core.exceptions import ValidationError

from scheduling.models import Event


@pytest.mark.django_db
def test_timezone_capacity_tenant_and_replay_contract():
    event = Event.objects.create(site_id='tenant-one', slug='launch', title='Launch', starts_at=datetime.now(UTC)+timedelta(days=1), ends_at=datetime.now(UTC)+timedelta(days=1,hours=1), timezone_name='Europe/Berlin', capacity=2, booking_open=True)
    event.full_clean()
    first, created = Event.reserve(event_id=event.id, site_id='tenant-one', attendee_ref='user-one', seats=1)
    assert created and first.seats == 1
    replay, created = Event.reserve(event_id=event.id, site_id='tenant-one', attendee_ref='user-one', seats=1)
    assert not created and replay.id == first.id
    Event.reserve(event_id=event.id, site_id='tenant-one', attendee_ref='user-two', seats=1)
    with pytest.raises(ValidationError, match='capacity_exceeded'):
        Event.reserve(event_id=event.id, site_id='tenant-one', attendee_ref='user-three', seats=1)
    with pytest.raises(Event.DoesNotExist):
        Event.reserve(event_id=event.id, site_id='tenant-two', attendee_ref='hostile', seats=1)


@pytest.mark.django_db
def test_invalid_timezone_and_naive_times_fail_closed():
    event = Event(site_id='tenant-one', slug='bad', title='Bad', starts_at=datetime.now(), ends_at=datetime.now()+timedelta(hours=1), timezone_name='Not/AZone', capacity=1)
    with pytest.raises(ValidationError):
        event.full_clean()
