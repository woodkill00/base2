from __future__ import annotations

import os
from contextlib import contextmanager
from uuid import UUID

import pytest
from api.services.email_service import (
    get_outbox_email,
    process_outbox_email,
    queue_email,
)
from api.db import close_pool

# These tests exercise real DB I/O via the outbox table; they belong in integration.
pytestmark = [pytest.mark.integration]


@contextmanager
def email_worker_database():
    """Exercise worker-only operations with the dedicated integration role."""
    worker_user = os.environ.get('EMAIL_WORKER_DB_USER', '')
    worker_password = os.environ.get('EMAIL_WORKER_DB_PASSWORD', '')
    if not worker_user or not worker_password:
        pytest.fail('email_worker_integration_credentials_missing')
    original_user = os.environ.get('DB_USER')
    original_password = os.environ.get('DB_PASSWORD')
    close_pool()
    os.environ['DB_USER'] = worker_user
    os.environ['DB_PASSWORD'] = worker_password
    try:
        yield
    finally:
        close_pool()
        if original_user is None:
            os.environ.pop('DB_USER', None)
        else:
            os.environ['DB_USER'] = original_user
        if original_password is None:
            os.environ.pop('DB_PASSWORD', None)
        else:
            os.environ['DB_PASSWORD'] = original_password


def test_queue_email_creates_outbox_row():
    outbox = queue_email(
        to_email='test@example.com',
        subject='Hello',
        body_text='Hello world',
        send_async=False,
    )
    with email_worker_database():
        fetched = get_outbox_email(UUID(str(outbox.id)))
    assert fetched is not None
    assert fetched.to_email == 'test@example.com'
    assert fetched.subject == 'Hello'
    assert fetched.body_text == 'Hello world'
    assert fetched.status in {'queued', 'sent'}


def test_process_outbox_marks_sent(monkeypatch):
    monkeypatch.setenv('BASE2_EMAIL_ADAPTER', 'local_fake')
    outbox = queue_email(
        to_email='test2@example.com',
        subject='Hello2',
        body_text='Hello world 2',
        send_async=False,
    )
    with email_worker_database():
        process_outbox_email(outbox_id=UUID(str(outbox.id)))
        fetched = get_outbox_email(UUID(str(outbox.id)))
    assert fetched is not None
    assert fetched.status == 'sent'
    assert fetched.sent_at is not None


def test_health_observer_reads_failure_using_worker_role():
    from api.db import db_conn
    from api.services.email_health import _outbox_requires_attention

    outbox = queue_email(
        to_email='health-fixture@example.com',
        subject='Synthetic health regression',
        body_text='Not sent',
        send_async=False,
    )
    # The API role may enqueue but deliberately cannot UPDATE or DELETE here.
    # Restore the synthetic row using the worker's existing UPDATE grant; tests
    # must not require a new DELETE privilege merely to clean up a status change.
    with email_worker_database():
        original = get_outbox_email(UUID(str(outbox.id)))
        assert original is not None
        try:
            with db_conn() as connection, connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE api_email_outbox SET status='dead_letter' WHERE id=%s",
                    (str(outbox.id),),
                )
                connection.commit()
            assert _outbox_requires_attention() is True
        finally:
            with db_conn() as connection, connection.cursor() as cursor:
                cursor.execute(
                    'UPDATE api_email_outbox SET status=%s WHERE id=%s',
                    (original.status, str(outbox.id)),
                )
                connection.commit()
        assert get_outbox_email(UUID(str(outbox.id))).status == original.status
