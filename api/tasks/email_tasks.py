from __future__ import annotations

import logging
from uuid import UUID

from api.services.email_service import process_outbox_email
from api.tasks import app
from contextlib import suppress


logger = logging.getLogger("api.email_tasks")


@app.task(bind=True, name="base2.send_email_outbox")
def send_email_outbox(self, outbox_id: str, request_id: str | None = None) -> str:
    with suppress(Exception):
        logger.info(
            "send_email_outbox",
            extra={"task_id": self.request.id, "request_id": request_id, "outbox_id": outbox_id},
        )

    process_outbox_email(outbox_id=UUID(outbox_id))
    return outbox_id
