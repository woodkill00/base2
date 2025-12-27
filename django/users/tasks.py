from __future__ import annotations

import logging

from celery import shared_task

from users.emails import queue_and_maybe_send_email, send_outbox_email
from users.models import EmailOutbox


logger = logging.getLogger("users.tasks")


@shared_task(bind=True)
def send_email_outbox(self, email_outbox_uuid: str, request_id: str | None = None) -> str:
    logger.info(
        "send_email_outbox",
        extra={"task_id": self.request.id, "request_id": request_id, "outbox_uuid": email_outbox_uuid},
    )
    outbox = EmailOutbox.objects.get(uuid=email_outbox_uuid)
    send_outbox_email(outbox)
    return email_outbox_uuid


# Keep deploy-time Celery probes stable: FastAPI enqueues `api.tasks.ping`.
@shared_task(bind=True, name="api.tasks.ping")
def ping(self, request_id: str | None = None):
    logger.info("ping", extra={"task_id": self.request.id, "request_id": request_id})
    return "pong"


# Deploy-time probes also enqueue `base2.ping` (legacy Celery app name).
@shared_task(name="base2.ping")
def ping_base2(request_id: str | None = None):
    # Keep this task signature permissive: deploy-time probes may pass request_id.
    try:
        logger.info("ping_base2", extra={"request_id": request_id})
    except Exception:
        pass
    return "pong"


@shared_task(bind=True)
def send_verification_email(self, *, to: str, verification_url: str, request_id: str | None = None) -> str:
    subject = "Verify your email"
    body = f"Verify your email by visiting: {verification_url}"
    logger.info(
        "send_verification_email",
        extra={"task_id": self.request.id, "request_id": request_id, "to": to},
    )
    outbox = queue_and_maybe_send_email(to=to, subject=subject, body=body)
    return str(outbox.uuid)


@shared_task(bind=True)
def send_password_reset_email(self, *, to: str, reset_url: str, request_id: str | None = None) -> str:
    subject = "Password reset"
    body = f"Reset your password by visiting: {reset_url}"
    logger.info(
        "send_password_reset_email",
        extra={"task_id": self.request.id, "request_id": request_id, "to": to},
    )
    outbox = queue_and_maybe_send_email(to=to, subject=subject, body=body)
    return str(outbox.uuid)
