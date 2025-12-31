from __future__ import annotations

from uuid import UUID

import pytest

# These tests exercise real DB I/O via the outbox table; they belong in integration.
pytestmark = [pytest.mark.integration]

from api.services.email_service import (
    get_outbox_email,
    process_outbox_email,
    queue_email,
)


def test_queue_email_creates_outbox_row():
    outbox = queue_email(
        to_email="test@example.com",
        subject="Hello",
        body_text="Hello world",
        send_async=False,
    )
    fetched = get_outbox_email(UUID(str(outbox.id)))
    assert fetched is not None
    assert fetched.to_email == "test@example.com"
    assert fetched.subject == "Hello"
    assert fetched.body_text == "Hello world"
    assert fetched.status in {"queued", "sent"}


def test_process_outbox_marks_sent():
    outbox = queue_email(
        to_email="test2@example.com",
        subject="Hello2",
        body_text="Hello world 2",
        send_async=False,
    )
    process_outbox_email(outbox_id=UUID(str(outbox.id)))

    fetched = get_outbox_email(UUID(str(outbox.id)))
    assert fetched is not None
    assert fetched.status == "sent"
    assert fetched.sent_at is not None
