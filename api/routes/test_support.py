from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Request

from api.db import db_conn


router = APIRouter()


def _require_e2e_key(request: Request) -> None:
    expected = (os.getenv("E2E_TEST_KEY", "") or "").strip()
    if not expected:
        raise HTTPException(status_code=500, detail="E2E test key not configured")

    provided = (request.headers.get("x-e2e-key", "") or "").strip()
    if provided != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.get("/test-support/outbox/latest")
async def outbox_latest(request: Request, to_email: str, subject_contains: str = ""):
    """E2E-only helper to fetch the latest outbox email for an address.

    Guarded by E2E_TEST_MODE + E2E_TEST_KEY; never enable in production.
    """

    _require_e2e_key(request)

    email = (to_email or "").strip().lower()
    if not email:
        raise HTTPException(status_code=422, detail="to_email is required")

    subj = (subject_contains or "").strip()
    subj_like = f"%{subj}%" if subj else "%"

    with db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, to_email, subject, body_text, body_html, status, created_at, sent_at
            FROM api_email_outbox
            WHERE lower(to_email)=lower(%s) AND subject ILIKE %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (email, subj_like),
        )
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="outbox_not_found")

    return {
        "id": str(row[0]),
        "to_email": row[1],
        "subject": row[2],
        "body_text": row[3] or "",
        "body_html": row[4] or "",
        "status": row[5] or "",
        "created_at": row[6],
        "sent_at": row[7],
    }
