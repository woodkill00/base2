import logging
import os
from contextlib import suppress
from uuid import UUID

from celery import Celery, Task

from api.services.email_service import process_outbox_email
from api.repositories.data_rights import expire_results, queued_operation_ids
from api.services.data_rights_worker import process_operation
from api.services.content_workspace_worker import (
    due_export_jobs,
    due_index_records,
    due_import_validations,
    due_media_scans,
    due_publication_ids,
    expire_export_jobs as expire_workspace_export_jobs,
    index_workspace_record,
    mark_export_failed,
    process_export_job,
    publish_scheduled_record,
    scan_workspace_asset,
    validate_import_job,
)
from api.services.content_workspace_storage import configured_artifact_store
from api.settings import settings


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
            'schedule': 60.0,
        },
        'workspace-process-exports': {
            'task': 'app.replay_workspace_exports',
            'schedule': 60.0,
        },
        'workspace-expire-exports': {
            'task': 'app.expire_workspace_exports',
            'schedule': 300.0,
        },
        'workspace-validate-imports': {
            'task': 'app.replay_workspace_import_validations',
            'schedule': 60.0,
        },
    },
)

# Ensure tasks are registered even when Celery starts before module import.
app.autodiscover_tasks(['api'])


@app.task(name='app.ping')
def ping(request_id: str | None = None):
    with suppress(Exception):
        logger.info('ping', extra={'request_id': request_id})
    return 'pong'


@app.task(name='app.add')
def add(x: int, y: int) -> int:
    return int(x) + int(y)


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
    )


@app.task(
    name='app.scan_workspace_asset',
    autoretry_for=(Exception,),
    dont_autoretry_for=(ValueError,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def scan_workspace_asset_task(site_id: str, asset_id: str) -> str:
    return scan_workspace_asset(
        site_id=site_id,
        asset_id=UUID(asset_id),
        artifact_store=_workspace_artifact_store(),
    )


@app.task(name='app.replay_workspace_media_scans')
def replay_workspace_media_scans(limit: int = 10) -> int:
    assets = due_media_scans(limit=limit)
    for site_id, asset_id in assets:
        scan_workspace_asset_task.delay(site_id, asset_id)
    return len(assets)


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
    return expire_workspace_export_jobs(limit=limit)


@app.task(
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
