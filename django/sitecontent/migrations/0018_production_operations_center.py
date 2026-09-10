import common.models
import django.core.validators
import django.db.models.deletion
import django.utils.timezone
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sitecontent', '0017_media_worker_rls_completion'),
    ]

    operations = [
        migrations.CreateModel(
            name='OperationsSyntheticRun',
            fields=[
                ('site_id', models.CharField(db_index=True, max_length=63, validators=[django.core.validators.RegexValidator('^[a-z][a-z0-9-]{2,62}$', 'Enter a canonical site identifier.')])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('journey_key', models.CharField(max_length=96, validators=[django.core.validators.RegexValidator('^[a-z][a-z0-9_.-]{2,95}$', 'Use a bounded lowercase operations identifier.')])),
                ('role', models.CharField(choices=[('anonymous', 'Anonymous'), ('member', 'Member'), ('editor', 'Editor'), ('administrator', 'Administrator')], max_length=16)),
                ('source_commit', models.CharField(max_length=40)),
                ('status', models.CharField(choices=[('running', 'Running'), ('passed', 'Passed'), ('failed', 'Failed')], max_length=16)),
                ('result_digest', models.CharField(blank=True, default='', max_length=64)),
                ('started_at', models.DateTimeField()),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='OperationsIncident',
            fields=[
                ('site_id', models.CharField(db_index=True, max_length=63, validators=[django.core.validators.RegexValidator('^[a-z][a-z0-9-]{2,62}$', 'Enter a canonical site identifier.')])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('fingerprint', models.CharField(max_length=64, validators=[django.core.validators.RegexValidator('^[a-f0-9]{64}$', 'Enter a lowercase SHA-256 digest.')])),
                ('severity', models.CharField(choices=[('info', 'Info'), ('warning', 'Warning'), ('high', 'High'), ('critical', 'Critical')], max_length=16)),
                ('state', models.CharField(choices=[('firing', 'Firing'), ('acknowledged', 'Acknowledged'), ('resolved', 'Resolved'), ('recurring', 'Recurring')], default='firing', max_length=16)),
                ('summary_code', models.CharField(max_length=96, validators=[django.core.validators.RegexValidator('^[a-z][a-z0-9_.-]{2,95}$', 'Use a bounded lowercase operations identifier.')])),
                ('owner_ref', models.CharField(blank=True, default='', max_length=200)),
                ('occurrence_count', models.PositiveIntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)])),
                ('first_observed_at', models.DateTimeField()),
                ('last_observed_at', models.DateTimeField()),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'indexes': [models.Index(fields=['site_id', 'state', '-last_observed_at'], name='operations_incident_idx')],
                'constraints': [models.UniqueConstraint(fields=('site_id', 'fingerprint'), name='operations_incident_scope_uq')],
            },
        ),
        migrations.CreateModel(
            name='OperationsIncidentEvent',
            fields=[
                ('site_id', models.CharField(db_index=True, max_length=63, validators=[django.core.validators.RegexValidator('^[a-z][a-z0-9-]{2,62}$', 'Enter a canonical site identifier.')])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('event_key', models.CharField(max_length=96, validators=[django.core.validators.RegexValidator('^[a-z][a-z0-9_.-]{2,95}$', 'Use a bounded lowercase operations identifier.')])),
                ('actor_ref', models.CharField(blank=True, default='system', max_length=200)),
                ('details', models.JSONField(default=dict, validators=[common.models.validate_operations_dimensions])),
                ('occurred_at', models.DateTimeField()),
                ('incident', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='timeline', to='sitecontent.operationsincident')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='OperationsObjective',
            fields=[
                ('site_id', models.CharField(db_index=True, max_length=63, validators=[django.core.validators.RegexValidator('^[a-z][a-z0-9-]{2,62}$', 'Enter a canonical site identifier.')])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('objective_key', models.CharField(max_length=96, validators=[django.core.validators.RegexValidator('^[a-z][a-z0-9_.-]{2,95}$', 'Use a bounded lowercase operations identifier.')])),
                ('indicator', models.CharField(max_length=96, validators=[django.core.validators.RegexValidator('^[a-z][a-z0-9_.-]{2,95}$', 'Use a bounded lowercase operations identifier.')])),
                ('target', models.DecimalField(decimal_places=5, max_digits=8)),
                ('window_minutes', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ('warning_threshold', models.DecimalField(decimal_places=5, max_digits=8)),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('site_id', 'objective_key'), name='operations_objective_scope_uq')],
            },
        ),
        migrations.CreateModel(
            name='OperationsService',
            fields=[
                ('site_id', models.CharField(db_index=True, max_length=63, validators=[django.core.validators.RegexValidator('^[a-z][a-z0-9-]{2,62}$', 'Enter a canonical site identifier.')])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('service_key', models.CharField(max_length=96, validators=[django.core.validators.RegexValidator('^[a-z][a-z0-9_.-]{2,95}$', 'Use a bounded lowercase operations identifier.')])),
                ('environment', models.CharField(choices=[('preview', 'Preview'), ('staging', 'Staging'), ('production', 'Production')], max_length=16)),
                ('enabled', models.BooleanField(default=True)),
                ('release_id', models.CharField(blank=True, default='', max_length=128)),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('site_id', 'environment', 'service_key'), name='operations_service_scope_uq')],
            },
        ),
        migrations.CreateModel(
            name='OperationsAlertDelivery',
            fields=[
                ('site_id', models.CharField(db_index=True, max_length=63, validators=[django.core.validators.RegexValidator('^[a-z][a-z0-9-]{2,62}$', 'Enter a canonical site identifier.')])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('channel', models.CharField(default='discord', max_length=32)),
                ('generation', models.PositiveIntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)])),
                ('status', models.CharField(choices=[('queued', 'Queued'), ('sent', 'Sent'), ('acknowledged', 'Acknowledged'), ('failed', 'Failed'), ('expired', 'Expired')], default='queued', max_length=16)),
                ('attempts', models.PositiveSmallIntegerField(default=0)),
                ('maximum_attempts', models.PositiveSmallIntegerField(default=5)),
                ('next_attempt_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('expires_at', models.DateTimeField()),
                ('receipt_digest', models.CharField(blank=True, default='', max_length=64)),
                ('error_code', models.CharField(blank=True, default='', max_length=96)),
                ('incident', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='deliveries', to='sitecontent.operationsincident')),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('site_id', 'incident', 'channel', 'generation'), name='operations_delivery_replay_uq')],
            },
        ),
        migrations.CreateModel(
            name='OperationsHealthSample',
            fields=[
                ('site_id', models.CharField(db_index=True, max_length=63, validators=[django.core.validators.RegexValidator('^[a-z][a-z0-9-]{2,62}$', 'Enter a canonical site identifier.')])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('state', models.CharField(choices=[('healthy', 'Healthy'), ('degraded', 'Degraded'), ('unavailable', 'Unavailable'), ('stale', 'Stale'), ('unknown', 'Unknown'), ('muted', 'Muted'), ('disabled', 'Disabled')], max_length=16)),
                ('code', models.CharField(max_length=96, validators=[django.core.validators.RegexValidator('^[a-z][a-z0-9_.-]{2,95}$', 'Use a bounded lowercase operations identifier.')])),
                ('latency_ms', models.PositiveIntegerField(blank=True, null=True)),
                ('dimensions', models.JSONField(default=dict, validators=[common.models.validate_operations_dimensions])),
                ('observed_at', models.DateTimeField()),
                ('expires_at', models.DateTimeField()),
                ('service', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='health_samples', to='sitecontent.operationsservice')),
            ],
            options={
                'indexes': [models.Index(fields=['site_id', 'service', '-observed_at'], name='operations_health_recent_idx')],
            },
        ),
    ]
