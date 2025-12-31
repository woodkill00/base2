import pytest
from django.utils import timezone

from users.emails import queue_and_maybe_send_email
from users.models import EmailOutbox


@pytest.mark.django_db
def test_email_outbox_created_without_smtp(settings):
    settings.EMAIL_HOST = ""

    outbox = queue_and_maybe_send_email(to="test@example.com", subject="Hello", body="World")

    assert outbox.to == "test@example.com"
    assert outbox.sent_at is None
    assert EmailOutbox.objects.filter(uuid=outbox.uuid).exists()


@pytest.mark.django_db
def test_email_outbox_marks_sent_when_smtp_configured(monkeypatch, settings):
    settings.EMAIL_HOST = "smtp.example.com"
    settings.DEFAULT_FROM_EMAIL = "noreply@example.com"

    sent = {"called": False}

    def _fake_send(self, fail_silently=False):
        sent["called"] = True
        return 1

    monkeypatch.setattr("django.core.mail.EmailMessage.send", _fake_send)

    outbox = queue_and_maybe_send_email(to="test@example.com", subject="Hello", body="World")

    assert sent["called"] is True
    assert outbox.sent_at is not None
    assert outbox.sent_at <= timezone.now()
