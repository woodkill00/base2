"""Lock ordering shared by native workspace helpers and API policy effects."""

from django.db import connection


def begin_workspace_policy_effect() -> None:
    """Acquire before native row locks; this does not grant a public identity.

    SQLite runs are model diagnostics only. PostgreSQL keeps this advisory lock
    until transaction completion, including rollback on any later guard failure.
    """
    if connection.vendor != "postgresql":
        return
    if not connection.in_atomic_block:
        raise RuntimeError("workspace_policy_transaction_required")
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", ("base2-workspace-policy-v1",))
