import logging
import os
from contextlib import suppress
from uuid import UUID

from celery import Celery

from api.services.email_service import process_outbox_email
from api.repositories.data_rights import expire_results, queued_operation_ids
from api.services.data_rights_worker import process_operation
from api.services.content_workspace_worker import due_publication_ids, publish_scheduled_record


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


@app.task(name='app.publish_workspace_record')
def publish_workspace_record(site_id: str, record_id: str) -> str:
    return publish_scheduled_record(site_id=site_id, record_id=UUID(record_id))


@app.task(name='app.replay_workspace_publications')
def replay_workspace_publications(limit: int = 25) -> int:
    records = due_publication_ids(limit=limit)
    for site_id, record_id in records:
        publish_workspace_record.delay(site_id, record_id)
    return len(records)
