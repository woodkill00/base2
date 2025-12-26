from __future__ import annotations

from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

from users.models import EmailOutbox


def _smtp_configured() -> bool:
    return bool(getattr(settings, "EMAIL_HOST", ""))


def create_outbox_email(*, to: str, subject: str, body: str) -> EmailOutbox:
    return EmailOutbox.objects.create(to=to, subject=subject, body=body)


def send_outbox_email(outbox: EmailOutbox) -> EmailOutbox:
    if outbox.sent_at:
        return outbox

    if not _smtp_configured():
        return outbox

    msg = EmailMessage(
        subject=outbox.subject,
        body=outbox.body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        to=[outbox.to],
    )
    msg.send(fail_silently=False)

    outbox.sent_at = timezone.now()
    outbox.save(update_fields=["sent_at"])
    return outbox


def queue_and_maybe_send_email(*, to: str, subject: str, body: str) -> EmailOutbox:
    outbox = create_outbox_email(to=to, subject=subject, body=body)
    return send_outbox_email(outbox)
