from __future__ import annotations

import uuid
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from sitecontent.models import SiteOwnedModel


class Event(SiteOwnedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=160)
    title = models.CharField(max_length=240)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    timezone_name = models.CharField(max_length=64)
    capacity = models.PositiveIntegerField()
    booking_open = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['site_id', 'slug'], name='scheduling_event_slug_uq'),
            models.CheckConstraint(condition=models.Q(capacity__gt=0), name='scheduling_capacity_gt_zero'),
            models.CheckConstraint(condition=models.Q(ends_at__gt=models.F('starts_at')), name='scheduling_end_after_start'),
        ]

    def clean(self):
        super().clean()
        try:
            ZoneInfo(self.timezone_name)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValidationError({'timezone_name': 'A valid IANA timezone is required.'}) from exc
        if timezone.is_naive(self.starts_at) or timezone.is_naive(self.ends_at):
            raise ValidationError({'starts_at': 'Timezone-aware start and end are required.'})

    @classmethod
    def reserve(cls, *, event_id, site_id: str, attendee_ref: str, seats: int = 1):
        if not attendee_ref or len(attendee_ref) > 128 or seats < 1 or seats > 20:
            raise ValidationError('booking_invalid')
        with transaction.atomic():
            event = cls.objects.select_for_update().for_tenant(site_id).get(id=event_id)
            if not event.booking_open or event.ends_at <= timezone.now():
                raise ValidationError('booking_closed')
            used = Booking.objects.filter(event=event, status=Booking.Status.CONFIRMED).aggregate(
                total=models.Sum('seats')
            )['total'] or 0
            if used + seats > event.capacity:
                raise ValidationError('capacity_exceeded')
            booking, created = Booking.objects.get_or_create(
                event=event,
                attendee_ref=attendee_ref,
                defaults={'site_id': site_id, 'seats': seats, 'status': Booking.Status.CONFIRMED},
            )
            if not created and (booking.seats != seats or booking.status != Booking.Status.CONFIRMED):
                raise ValidationError('booking_replay_conflict')
            return booking, created


class Booking(SiteOwnedModel):
    class Status(models.TextChoices):
        CONFIRMED = 'confirmed', 'Confirmed'
        CANCELLED = 'cancelled', 'Cancelled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='bookings')
    attendee_ref = models.CharField(max_length=128)
    seats = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.CONFIRMED)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['event', 'attendee_ref'], name='scheduling_booking_replay_uq'),
            models.CheckConstraint(condition=models.Q(seats__gt=0), name='scheduling_booking_seats_gt_zero'),
        ]

    def clean(self):
        super().clean()
        if self.event_id and self.site_id != self.event.site_id:
            raise ValidationError({'site_id': 'booking_tenant_mismatch'})
