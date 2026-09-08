import hashlib
import json
import logging
import os
from contextlib import suppress
from datetime import UTC, datetime
from uuid import UUID

from celery import Celery, Task
from celery.signals import before_task_publish, heartbeat_sent, task_prerun, worker_ready

from api.services.email_service import process_outbox_email
from api.repositories.operations import prune as prune_operations
from api.repositories.data_rights import expire_results, queued_operation_ids
from api.services.data_rights_worker import process_operation
from api.services.content_workspace_worker import (
    begin_media_scan_attempt,
    due_export_jobs,
    due_index_records,
    due_import_validations,
    due_import_commits,
    due_media_scans,
    due_publication_ids,
    expire_export_jobs as expire_workspace_export_jobs,
    finish_media_scan_attempt,
    index_workspace_record,
    mark_export_failed,
    mark_import_failed,
    purge_workspace_retention,
    process_export_job,
    process_import_commit,
    publish_scheduled_record,
    recover_media_scan_attempt,
    validate_import_job,
)
from api.services.content_workspace_storage import configured_artifact_store
from api.services.media_library_runtime import (
    apply_due_media_governance,
    due_media_exports,
    process_governed_media_asset as scan_workspace_asset,
    process_media_export,
)
from api.settings import SITE_MANIFEST, settings
from api.repositories.runtime_governance import (
    claim_due_schedules,
    claim_jobs,
    enqueue_job,
    renew_job_lease,
    settle_job,
    settle_schedule_claim,
)
from api.services.operations_runtime import (
    collect_site,
    configured_tenants,
    discord_webhook_sender,
    dispatch_alerts,
    fair_tenant_batch,
    mark_queue_observation,
    mark_runtime_heartbeat,
)


logger = logging.getLogger('api.tasks')

# Broker/backends from environment; defaults align with .env.example
BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/1')

app = Celery(
    'app',
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    fixups=[],
)

# Basic config can be extended as needed
app.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='UTC',
    enable_utc=True,
    include=['api.tasks'],
    beat_schedule={
        'replay-data-rights-queue': {
            'task': 'app.replay_data_rights_operations',
            'schedule': 300.0,
        },
        'expire-data-rights-results': {
            'task': 'app.expire_data_rights_results',
            'schedule': 86400.0,
        },
        'workspace-publish-scheduled': {
            'task': 'app.replay_workspace_publications',
            'schedule': 60.0,
        },
        'workspace-refresh-search-index': {
            'task': 'app.replay_workspace_indexing',
            'schedule': 60.0,
        },
        'workspace-scan-quarantined-media': {
            'task': 'app.replay_workspace_media_scans',
            # Keep admission responsive while due_media_scans retains the
            # durable lease, retry, and concurrency boundary.
            'schedule': 15.0,
        },
        'media-process-exports': {
            'task': 'app.replay_media_exports',
            'schedule': 60.0,
        },
        'media-apply-reviewed-governance': {
            'task': 'app.apply_media_governance',
            'schedule': 300.0,
        },
        'workspace-process-exports': {
            'task': 'app.replay_workspace_exports',
            'schedule': 60.0,
        },
        'workspace-expire-exports': {
            'task': 'app.expire_workspace_exports',
            'schedule': 300.0,
        },
        'workspace-retention-cleanup': {
            'task': 'app.purge_workspace_retained_data',
            'schedule': 86400.0,
        },
        'workspace-validate-imports': {
            'task': 'app.replay_workspace_import_validations',
            'schedule': 60.0,
        },
        'workspace-commit-imports': {
            'task': 'app.replay_workspace_import_commits',
            'schedule': 60.0,
        },
        'operations-collect-health': {
            'task': 'app.collect_operations_health',
            'schedule': 60.0,
        },
        'operations-dispatch-alerts': {
            'task': 'app.dispatch_operations_alerts',
            'schedule': 30.0,
        },
        'operations-retention': {
            'task': 'app.prune_operations_evidence',
            'schedule': 86400.0,
        },
        'runtime-materialize-schedules': {
            'task': 'app.materialize_runtime_schedules',
            'schedule': 30.0,
        },
        'runtime-claim-jobs': {
            'task': 'app.claim_runtime_jobs',
            'schedule': 15.0,
        },
    },
)

# Ensure tasks are registered even when Celery starts before module import.
app.autodiscover_tasks(['api'])


@before_task_publish.connect
def _stamp_published_at(headers=None, **_kwargs):
    if isinstance(headers, dict):
        headers['base2PublishedAt'] = datetime.now(UTC).isoformat()


@worker_ready.connect
@heartbeat_sent.connect
def _observe_worker(**_kwargs):
    with suppress(Exception):
        mark_runtime_heartbeat('workers')


@task_prerun.connect
def _observe_queue_delay(task=None, **_kwargs):
    with suppress(Exception):
        raw = getattr(getattr(task, 'request', None), 'headers', {}).get('base2PublishedAt')
        mark_queue_observation(published_at=datetime.fromisoformat(str(raw)))


@app.task(name='app.ping')
def ping(request_id: str | None = None):
    with suppress(Exception):
        logger.info('ping', extra={'request_id': request_id})
    return 'pong'


@app.task(name='app.add')
def add(x: int, y: int) -> int:
    return int(x) + int(y)


@app.task(name='app.collect_operations_site')
def collect_operations_site(site_id: str) -> dict[str, int]:
    environment = (
        settings.ENV if settings.ENV in {'preview', 'staging', 'production'} else 'preview'
    )
    return collect_site(tenant_id=site_id, environment=environment)


@app.task(name='app.collect_operations_health')
def collect_operations_health() -> int:
    tenants = fair_tenant_batch(configured_tenants())
    for tenant_id in tenants:
        collect_operations_site.delay(tenant_id)
    return len(tenants)


@app.task(name='app.dispatch_operations_site_alerts')
def dispatch_operations_site_alerts(site_id: str) -> dict[str, int]:
    return dispatch_alerts(tenant_id=site_id, sender=discord_webhook_sender)


@app.task(name='app.dispatch_operations_alerts')
def dispatch_operations_alerts_task() -> int:
    if not settings.OPERATIONS_ALERTS_ENABLED:
        return 0
    tenants = configured_tenants()
    for tenant_id in tenants:
        dispatch_operations_site_alerts.delay(tenant_id)
    return len(tenants)


@app.task(name='app.prune_operations_evidence')
def prune_operations_evidence() -> dict[str, dict[str, int]]:
    return {tenant_id: prune_operations(tenant_id=tenant_id) for tenant_id in configured_tenants()}


RUNTIME_JOB_TYPES = frozenset({'operations.collect', 'operations.alerts', 'operations.prune'})


def _runtime_digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
    ).hexdigest()


@app.task(name='app.materialize_runtime_schedules')
def materialize_runtime_schedules() -> int:
    """Turn due fixed schedules into replay-safe jobs and release every claim."""
    now = datetime.now(UTC)
    materialized = 0
    for tenant_id in configured_tenants():
        for schedule in claim_due_schedules(tenant_id=tenant_id, now=now, limit=25):
            original_due = datetime.fromisoformat(schedule['scheduledFor'])
            succeeded = False
            try:
                if schedule['jobType'] not in RUNTIME_JOB_TYPES:
                    raise ValueError('schedule:job_type_not_allowed')
                identity = {
                    'scheduleId': schedule['scheduleId'],
                    'scheduleKey': schedule['scheduleKey'],
                    'jobType': schedule['jobType'],
                    'scheduledFor': schedule['scheduledFor'],
                    'revision': schedule['revision'],
                }
                enqueue_job(
                    tenant_id=tenant_id,
                    owner_ref=f"schedule:{schedule['scheduleId']}",
                    job_type=schedule['jobType'],
                    payload_digest=_runtime_digest(identity),
                    payload_schema=1,
                    idempotency_key=(
                        f"schedule:{schedule['scheduleId']}:{schedule['scheduledFor']}"
                    ),
                    available_at=now,
                )
                succeeded = True
                materialized += 1
            finally:
                settle_schedule_claim(
                    tenant_id=tenant_id,
                    schedule_id=UUID(schedule['scheduleId']),
                    claim_token=UUID(schedule['claimToken']),
                    revision=int(schedule['revision']),
                    succeeded=succeeded,
                    original_next_run_at=original_due,
                )
    mark_runtime_heartbeat('schedules', now=now)
    return materialized


@app.task(name='app.run_runtime_job')
def run_runtime_job(tenant_id: str, job: dict) -> str:
    worker = 'base2-runtime-v1'
    now = datetime.now(UTC)
    renew_job_lease(
        tenant_id=tenant_id,
        job_id=UUID(job['jobId']),
        worker=worker,
        lease_token=UUID(job['leaseToken']),
        generation=int(job['generation']),
        now=now,
    )
    try:
        job_type = str(job['jobType'])
        if job_type == 'operations.collect':
            result = collect_operations_site(tenant_id)
        elif job_type == 'operations.alerts':
            result = dispatch_operations_site_alerts(tenant_id)
        elif job_type == 'operations.prune':
            result = prune_operations(tenant_id=tenant_id)
        else:
            raise ValueError('job:type_not_allowed')
    except Exception as exc:
        return settle_job(
            tenant_id=tenant_id,
            job_id=UUID(job['jobId']),
            worker=worker,
            lease_token=UUID(job['leaseToken']),
            generation=int(job['generation']),
            outcome='retry',
            now=now,
            error_code=(str(exc) if isinstance(exc, ValueError) else 'job.execution_failed')[:96],
        )
    return settle_job(
        tenant_id=tenant_id,
        job_id=UUID(job['jobId']),
        worker=worker,
        lease_token=UUID(job['leaseToken']),
        generation=int(job['generation']),
        outcome='succeeded',
        now=now,
        result_digest=_runtime_digest(result),
    )


@app.task(name='app.claim_runtime_jobs')
def claim_runtime_jobs_task() -> int:
    now = datetime.now(UTC)
    claimed = 0
    for tenant_id in configured_tenants():
        jobs = claim_jobs(tenant_id=tenant_id, worker='base2-runtime-v1', now=now, limit=10)
        for job in jobs:
            run_runtime_job.delay(tenant_id, job)
        claimed += len(jobs)
    return claimed


@app.task(bind=True, name='app.send_email_outbox')
def send_email_outbox(self, outbox_id: str, request_id: str | None = None) -> str:
    with suppress(Exception):
        logger.info(
            'send_email_outbox',
            extra={'task_id': self.request.id, 'request_id': request_id, 'outbox_id': outbox_id},
        )

    process_outbox_email(outbox_id=UUID(outbox_id))
    return outbox_id


@app.task(name='app.process_data_rights_operation')
def process_data_rights_operation(operation_id: str) -> str:
    return process_operation(UUID(operation_id))


@app.task(name='app.expire_data_rights_results')
def expire_data_rights_results() -> int:
    return expire_results()


@app.task(name='app.replay_data_rights_operations')
def replay_data_rights_operations(limit: int = 25) -> int:
    operation_ids = queued_operation_ids(limit=limit)
    for operation_id in operation_ids:
        process_data_rights_operation.delay(str(operation_id))
    return len(operation_ids)


class WorkspaceExportTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        del task_id, kwargs, einfo
        if len(args) >= 2:
            error_code = str(exc) if isinstance(exc, ValueError) else ''
            with suppress(Exception):
                mark_export_failed(
                    site_id=str(args[0]), job_id=UUID(str(args[1])), error_code=error_code
                )


class WorkspaceImportTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        del task_id, kwargs, einfo
        if len(args) >= 2:
            error_code = str(exc) if isinstance(exc, ValueError) else ''
            with suppress(Exception):
                mark_import_failed(
                    site_id=str(args[0]), job_id=UUID(str(args[1])), error_code=error_code
                )


@app.task(
    name='app.publish_workspace_record',
    autoretry_for=(Exception,),
    dont_autoretry_for=(ValueError,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def publish_workspace_record(site_id: str, record_id: str) -> str:
    return publish_scheduled_record(site_id=site_id, record_id=UUID(record_id))


@app.task(name='app.replay_workspace_publications')
def replay_workspace_publications(limit: int = 25) -> int:
    records = due_publication_ids(limit=limit)
    for site_id, record_id in records:
        publish_workspace_record.delay(site_id, record_id)
    return len(records)


@app.task(
    name='app.index_workspace_record',
    autoretry_for=(Exception,),
    dont_autoretry_for=(ValueError,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def index_workspace_record_task(site_id: str, record_id: str, version: int) -> str:
    return index_workspace_record(
        site_id=site_id,
        record_id=UUID(record_id),
        job_version=version,
    )


@app.task(name='app.replay_workspace_indexing')
def replay_workspace_indexing(limit: int = 25) -> int:
    records = due_index_records(limit=limit)
    for site_id, record_id, version in records:
        index_workspace_record_task.delay(site_id, record_id, version)
    return len(records)


def _workspace_artifact_store():
    return configured_artifact_store(
        root=settings.CONTENT_WORKSPACE_STORAGE_ROOT,
        encoded_key=settings.CONTENT_WORKSPACE_STORAGE_KEY or '',
        max_bytes=int(SITE_MANIFEST.get('media', {}).get('maxBytes', 10 * 1024 * 1024)),
    )


@app.task(
    name='app.scan_workspace_asset',
)
def scan_workspace_asset_task(
    site_id: str, asset_id: str, job_id: str, attempt: int, lease_token: str
) -> str:
    token = datetime.fromisoformat(lease_token)
    if not begin_media_scan_attempt(
        site_id=site_id,
        asset_id=UUID(asset_id),
        job_id=UUID(job_id),
        attempt=attempt,
        lease_token=token,
    ):
        return 'stale_attempt'
    try:
        result = scan_workspace_asset(
            site_id=site_id,
            asset_id=UUID(asset_id),
            artifact_store=_workspace_artifact_store(),
        )
    except Exception:
        try:
            recover_media_scan_attempt(
                site_id=site_id,
                job_id=UUID(job_id),
                attempt=attempt,
                lease_token=token,
            )
        except Exception:
            logger.error('media_scan_recovery_failed')
        raise
    finish_media_scan_attempt(
        site_id=site_id,
        job_id=UUID(job_id),
        attempt=attempt,
        lease_token=token,
        result=result,
    )
    return result


@app.task(name='app.replay_workspace_media_scans')
def replay_workspace_media_scans(limit: int = 10) -> int:
    assets = due_media_scans(limit=limit)
    for site_id, asset_id, job_id, attempt, lease_token in assets:
        scan_workspace_asset_task.delay(site_id, asset_id, job_id, attempt, lease_token)
    return len(assets)


@app.task(
    name='app.process_media_export',
    autoretry_for=(Exception,),
    dont_autoretry_for=(ValueError,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def process_media_export_task(site_id: str, export_id: str) -> str:
    return process_media_export(
        site_id=site_id,
        export_id=UUID(export_id),
        artifact_store=_workspace_artifact_store(),
    )


@app.task(name='app.replay_media_exports')
def replay_media_exports(limit: int = 10) -> int:
    packages = due_media_exports(limit=limit)
    for site_id, export_id in packages:
        process_media_export_task.delay(site_id, export_id)
    return len(packages)


@app.task(name='app.apply_media_governance')
def apply_media_governance(limit: int = 100) -> dict[str, int]:
    return apply_due_media_governance(limit=limit)


@app.task(
    base=WorkspaceExportTask,
    name='app.process_workspace_export',
    autoretry_for=(Exception,),
    dont_autoretry_for=(ValueError,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def process_workspace_export(site_id: str, job_id: str) -> str:
    return process_export_job(
        site_id=site_id,
        job_id=UUID(job_id),
        artifact_store=_workspace_artifact_store(),
    )


@app.task(name='app.replay_workspace_exports')
def replay_workspace_exports(limit: int = 10) -> int:
    jobs = due_export_jobs(limit=limit)
    for site_id, job_id in jobs:
        process_workspace_export.delay(site_id, job_id)
    return len(jobs)


@app.task(name='app.expire_workspace_exports')
def expire_workspace_exports(limit: int = 100) -> int:
    return expire_workspace_export_jobs(artifact_store=_workspace_artifact_store(), limit=limit)


@app.task(name='app.purge_workspace_retained_data')
def purge_workspace_retained_data(limit: int = 100) -> dict:
    return purge_workspace_retention(artifact_store=_workspace_artifact_store(), limit=limit)


@app.task(
    base=WorkspaceImportTask,
    name='app.validate_workspace_import',
    autoretry_for=(Exception,),
    dont_autoretry_for=(ValueError,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def validate_workspace_import(site_id: str, job_id: str) -> str:
    return validate_import_job(
        site_id=site_id,
        job_id=UUID(job_id),
        artifact_store=_workspace_artifact_store(),
    )


@app.task(name='app.replay_workspace_import_validations')
def replay_workspace_import_validations(limit: int = 10) -> int:
    jobs = due_import_validations(limit=limit)
    for site_id, job_id in jobs:
        validate_workspace_import.delay(site_id, job_id)
    return len(jobs)


@app.task(
    base=WorkspaceImportTask,
    name='app.commit_workspace_import',
    autoretry_for=(Exception,),
    dont_autoretry_for=(ValueError,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def commit_workspace_import(site_id: str, job_id: str) -> str:
    return process_import_commit(
        site_id=site_id,
        job_id=UUID(job_id),
        artifact_store=_workspace_artifact_store(),
    )


@app.task(name='app.replay_workspace_import_commits')
def replay_workspace_import_commits(limit: int = 10) -> int:
    jobs = due_import_commits(limit=limit)
    for site_id, job_id in jobs:
        commit_workspace_import.delay(site_id, job_id)
    return len(jobs)
