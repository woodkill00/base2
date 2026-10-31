"""Trusted, disposable Compose CLI. Never imported by or routed through the API.

Seed is one-shot owner setup. Observation/controlled-clock consumption use the
production content-worker role. No arbitrary SQL, tenant, recipient or role input.
Asset readiness is a synthetic fixture, NOT evidence of media scanning.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5


def selected_profile() -> str:
    profile = os.environ.get("E2E_SITE_PROFILE", "base2-obsidian")
    if (
        profile not in {"base2-obsidian", "journey-reference"}
        or os.getenv("SITE_PROFILE", profile) != profile
    ):
        raise RuntimeError("workspace_disposable_profile_required")
    import api

    manifest_path = Path(api.__file__).parent / "site_profiles" / f"{profile}.json"
    manifest = json.loads(manifest_path.read_text())
    enabled = {module["id"] for module in manifest["modules"] if module["enabled"]}
    required = {"accounts", "content-workspace"}
    if profile == "journey-reference":
        required |= {"blog", "documentation", "portfolio"}
    if manifest["siteId"] != profile or not required <= enabled:
        raise RuntimeError("workspace_disposable_profile_manifest_invalid")
    return profile


SITE = selected_profile()
IDENTITY_NAMESPACE = "base2-e2e-124" if SITE == "base2-obsidian" else f"base2-e2e-124/{SITE}"
PASSWORD = "SyntheticE2e124!Password"
ACTORS = {
    name: str(uuid5(NAMESPACE_URL, f"{IDENTITY_NAMESPACE}/{name}"))
    for name in ("owner", "editor", "reviewer", "viewer", "suspended", "outsider")
}
ASSET = str(uuid5(NAMESPACE_URL, f"{IDENTITY_NAMESPACE}/asset"))
ORG = str(uuid5(NAMESPACE_URL, f"{IDENTITY_NAMESPACE}/organization"))


def guard(*, seed: bool) -> None:
    if selected_profile() != SITE:
        raise RuntimeError("workspace_disposable_profile_changed")
    expected = {
        "ENV": "test",
        "E2E_WORKSPACE_DISPOSABLE": "1",
        "DB_HOST": "postgres",
        "DB_PORT": "5432",
        "DB_NAME": "e2e",
        "SITE_PROFILE": SITE,
        "DB_USER": "e2e" if seed else "base2_workspace_worker_e2e",
        "BASE2_PROCESS_ROLE": "migration" if seed else "content-worker",
    }
    if seed:
        expected["CONTENT_WORKSPACE_STORAGE_BACKEND"] = "local"
        expected["CONTENT_WORKSPACE_STORAGE_ROOT"] = "/var/lib/base2/content-workspace"
    else:
        expected["WORKSPACE_WORKER_DB_USER"] = "base2_workspace_worker_e2e"
    if any(os.getenv(key) != value for key, value in expected.items()) or os.getenv("DATABASE_URL"):
        raise RuntimeError("workspace_disposable_environment_required")


def control_clock(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    now = datetime.now(UTC)
    if result.tzinfo is None or result.utcoffset() != timedelta(0):
        raise ValueError("controlled_clock_requires_utc")
    if not now - timedelta(minutes=5) <= result <= now + timedelta(days=2):
        raise ValueError("controlled_clock_outside_disposable_window")
    return result


def identities() -> dict:
    return {
        "site": SITE,
        "assetId": ASSET,
        "actors": {
            name: {"id": value, "email": f"workspace124-{name}@example.test"}
            for name, value in ACTORS.items()
        },
    }


def seed() -> dict:
    guard(seed=True)
    import psycopg2

    from api.auth.passwords import hash_password
    from api.services.content_workspace_storage import configured_runtime_artifact_store
    from api.settings import SITE_MANIFEST, settings

    if SITE_MANIFEST["siteId"] != SITE:
        raise RuntimeError("workspace_disposable_manifest_mismatch")
    # A valid 1px PNG, intentionally pre-inspected fixture. Never caller supplied.
    content = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aP9sAAAAASUVORK5CYII="
    )
    store = configured_runtime_artifact_store(settings, max_bytes=1024 * 1024)
    with (
        psycopg2.connect(
            host="postgres", dbname="e2e", user="e2e", password=os.environ["DB_PASSWORD"]
        ) as conn,
        conn.cursor() as cur,
    ):
        cur.execute("SELECT current_user,current_database()")
        if cur.fetchone() != ("e2e", "e2e"):
            raise RuntimeError("workspace_disposable_database_mismatch")
        cur.execute("SELECT count(*) FROM api_auth_users")
        if cur.fetchone()[0] != 0:
            raise RuntimeError("workspace_disposable_seed_requires_empty_auth_database")
        cur.execute("SELECT count(*) FROM api_identity_organizations")
        if cur.fetchone()[0] != 0:
            raise RuntimeError("workspace_disposable_seed_requires_empty_organizations")
        cur.execute("SELECT set_config('app.tenant_id',%s,true)", (SITE,))
        for name, user_id in ACTORS.items():
            cur.execute(
                "INSERT INTO api_auth_users(id,email,password_hash,is_email_verified) VALUES(%s,%s,%s,true)",
                (user_id, identities()["actors"][name]["email"], hash_password(PASSWORD)),
            )
        cur.execute(
            "INSERT INTO api_identity_organizations(id,tenant_id,name) VALUES(%s,%s,%s)",
            (ORG, SITE, "Disposable workspace acceptance"),
        )
        for name, role in [
            ("owner", "owner"),
            ("editor", "editor"),
            ("reviewer", "admin"),
            ("viewer", "viewer"),
            ("suspended", "viewer"),
        ]:
            cur.execute(
                "INSERT INTO api_identity_memberships(organization_id,user_id,role,status) VALUES(%s,%s,%s,%s)",
                (ORG, ACTORS[name], role, "suspended" if name == "suspended" else "active"),
            )
        artifact = store.put(
            namespace="variants", site_id=SITE, object_id=f"{ASSET}-safe", content=content
        )
        cur.execute(
            """INSERT INTO sitecontent_mediaasset
            (id,site_id,storage_key,original_name,media_type,byte_size,sha256,status,
             owner_ref,attribution,metadata,visibility,lock_version,current_object_version,
             authorization_epoch,created_at,updated_at)
            VALUES (%s,%s,%s,'synthetic.png','image/png',%s,%s,'ready',%s,'',
                    '{"e2e":"synthetic-readiness-not-scanning"}','public',1,1,1,NOW(),NOW())""",
            (
                ASSET,
                SITE,
                artifact.object_key,
                artifact.byte_size,
                artifact.sha256,
                f'user:{ACTORS["editor"]}',
            ),
        )
        cur.execute(
            """INSERT INTO sitecontent_mediavariant
            (id,asset_id,name,storage_key,media_type,byte_size,sha256,recipe_id,recipe_version,
             source_sha256,processor_ref,inline_safe,created_at)
            VALUES (%s,%s,'safe',%s,'image/png',%s,%s,'e2e-fixture',1,%s,'synthetic-fixture',true,NOW())""",
            (
                str(uuid5(NAMESPACE_URL, f"{IDENTITY_NAMESPACE}/variant")),
                ASSET,
                artifact.object_key,
                artifact.byte_size,
                artifact.sha256,
                artifact.sha256,
            ),
        )
    return {"ready": True, **identities()}


def validate_owned_fixture(organization, users) -> None:
    expected_users = {
        (value, identities()["actors"][name]["email"]) for name, value in ACTORS.items()
    }
    if (
        organization != (ORG, SITE, "Disposable workspace acceptance")
        or len(users) != len(expected_users)
        or {(str(user_id), email) for user_id, email in users} != expected_users
    ):
        raise RuntimeError("workspace_disposable_fixture_ownership_mismatch")


def suspend_viewer() -> dict:
    """Fixed fixture-only revocation, NOT a user-facing membership API proof."""
    guard(seed=True)  # owner credentials stay only in the one-shot setup service
    import psycopg2

    from api.repositories.workspace_policy import begin_effect

    with (
        psycopg2.connect(
            host="postgres", dbname="e2e", user="e2e", password=os.environ["DB_PASSWORD"]
        ) as conn,
        conn.cursor() as cur,
    ):
        cur.execute("SELECT current_user,current_database()")
        if cur.fetchone() != ("e2e", "e2e"):
            raise RuntimeError("workspace_disposable_database_mismatch")
        cur.execute("SELECT set_config('app.tenant_id',%s,true)", (SITE,))
        begin_effect(cur, actor_ref=f'user:{ACTORS["owner"]}')
        cur.execute(
            "SELECT id::text,tenant_id,name FROM api_identity_organizations WHERE id=%s FOR UPDATE",
            (ORG,),
        )
        organization = cur.fetchone()
        cur.execute(
            "SELECT id,email FROM api_auth_users WHERE id=ANY(%s::uuid[]) ORDER BY id FOR UPDATE",
            (list(ACTORS.values()),),
        )
        validate_owned_fixture(organization, cur.fetchall())
        cur.execute(
            """UPDATE api_identity_memberships SET status='suspended',updated_at=NOW()
            WHERE organization_id=%s AND user_id=%s AND role='viewer' AND status='active'
            RETURNING user_id""",
            (ORG, ACTORS["viewer"]),
        )
        if cur.fetchone() is None:
            raise RuntimeError("workspace_disposable_viewer_not_active")
    return {
        "proofKind": "fixture-driven-membership-suspension-not-user-facing-flow",
        "actorId": ACTORS["viewer"],
        "status": "suspended",
    }


def snapshot() -> dict:
    guard(seed=False)
    from api.db import workspace_worker_db_conn
    from api.settings import SITE_MANIFEST

    if SITE_MANIFEST["siteId"] != SITE:
        raise RuntimeError("workspace_disposable_manifest_mismatch")
    with workspace_worker_db_conn(tenant_id=SITE) as conn, conn.cursor() as cur:
        cur.execute("SELECT current_user,current_database()")
        role, database = cur.fetchone()
        if (role, database) != ("base2_workspace_worker_e2e", "e2e"):
            raise RuntimeError("workspace_disposable_worker_role_mismatch")
        cur.execute(
            """SELECT id,record_id,recipient_id,status,digest_batch_id,available_at
            FROM sitecontent_reviewnotificationintent WHERE site_id=%s ORDER BY id LIMIT 1000""",
            (SITE,),
        )
        intents = [
            dict(
                zip(
                    ("id", "recordId", "recipientId", "status", "batchId", "availableAt"),
                    row,
                    strict=True,
                )
            )
            for row in cur.fetchall()
        ]
        cur.execute(
            """SELECT effect_key,recipient_id,intent_id,digest_batch_id
            FROM sitecontent_reviewnotificationdelivery WHERE site_id=%s ORDER BY effect_key LIMIT 1000""",
            (SITE,),
        )
        receipts = [
            dict(zip(("effectKey", "recipientId", "intentId", "batchId"), row, strict=True))
            for row in cur.fetchall()
        ]
        cur.execute(
            """SELECT action,object_ref FROM sitecontent_workspaceauditevent
            WHERE site_id=%s AND actor_ref='system:scheduler' ORDER BY created_at LIMIT 1000""",
            (SITE,),
        )
        scheduler = [dict(zip(("action", "recordId"), row, strict=True)) for row in cur.fetchall()]
    return {
        **identities(),
        "databaseRole": role,
        "intents": intents,
        "receipts": receipts,
        "scheduler": scheduler,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("seed", "snapshot", "consume", "suspend-viewer"))
    parser.add_argument("--now")
    args = parser.parse_args(argv)
    if args.now and args.command != "consume":
        parser.error("--now is only valid for controlled consumption")
    if args.command == "seed":
        result = seed()
    elif args.command == "suspend-viewer":
        result = suspend_viewer()
    elif args.command == "snapshot":
        result = snapshot()
    else:
        guard(seed=False)
        if not args.now:
            parser.error("consume requires an explicit controlled --now UTC timestamp")
        from api.services.workspace_review_notifications import process_review_notifications

        result = {
            "proofKind": "direct-controlled-clock-service-not-beat",
            "counts": process_review_notifications(site_id=SITE, now=control_clock(args.now)),
        }
    print(json.dumps(result, default=str, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
