from __future__ import annotations

from celery import shared_task

from users.emails import queue_and_maybe_send_email, send_outbox_email
from users.models import EmailOutbox


@shared_task
def send_email_outbox(email_outbox_uuid: str) -> str:
    outbox = EmailOutbox.objects.get(uuid=email_outbox_uuid)
    send_outbox_email(outbox)
    return email_outbox_uuid


# Keep deploy-time Celery probes stable: FastAPI enqueues `api.tasks.ping`.
@shared_task(name="api.tasks.ping")
def ping():
    return "pong"


# Deploy-time probes also enqueue `base2.ping` (legacy Celery app name).
@shared_task(name="base2.ping")
def ping_base2():
    return "pong"


@shared_task
def send_verification_email(*, to: str, verification_url: str) -> str:
    subject = "Verify your email"
    body = f"Verify your email by visiting: {verification_url}"
    outbox = queue_and_maybe_send_email(to=to, subject=subject, body=body)
    return str(outbox.uuid)


@shared_task
def send_password_reset_email(*, to: str, reset_url: str) -> str:
    subject = "Password reset"
    body = f"Reset your password by visiting: {reset_url}"
    outbox = queue_and_maybe_send_email(to=to, subject=subject, body=body)
    return str(outbox.uuid)
