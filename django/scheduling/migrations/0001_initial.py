import django.db.models.deletion
import django.core.validators
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(name='Event', fields=[
            ('site_id', models.CharField(db_index=True, max_length=63, validators=[django.core.validators.RegexValidator('^[a-z][a-z0-9-]{2,62}$', 'Enter a canonical site identifier.')])), ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)),
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)), ('slug', models.SlugField(max_length=160)), ('title', models.CharField(max_length=240)), ('starts_at', models.DateTimeField()), ('ends_at', models.DateTimeField()), ('timezone_name', models.CharField(max_length=64)), ('capacity', models.PositiveIntegerField()), ('booking_open', models.BooleanField(default=False)),
        ], options={'constraints':[models.UniqueConstraint(fields=('site_id','slug'),name='scheduling_event_slug_uq'),models.CheckConstraint(condition=models.Q(('capacity__gt',0)),name='scheduling_capacity_gt_zero'),models.CheckConstraint(condition=models.Q(('ends_at__gt',models.F('starts_at'))),name='scheduling_end_after_start')]}),
        migrations.CreateModel(name='Booking', fields=[
            ('site_id', models.CharField(db_index=True, max_length=63, validators=[django.core.validators.RegexValidator('^[a-z][a-z0-9-]{2,62}$', 'Enter a canonical site identifier.')])), ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)),
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)), ('attendee_ref', models.CharField(max_length=128)), ('seats', models.PositiveSmallIntegerField()), ('status', models.CharField(choices=[('confirmed','Confirmed'),('cancelled','Cancelled')],default='confirmed',max_length=16)), ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='bookings',to='scheduling.event')),
        ], options={'constraints':[models.UniqueConstraint(fields=('event','attendee_ref'),name='scheduling_booking_replay_uq'),models.CheckConstraint(condition=models.Q(('seats__gt',0)),name='scheduling_booking_seats_gt_zero')]}),
    ]
