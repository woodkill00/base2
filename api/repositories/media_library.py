"""Tenant-scoped persistence for the media library read and metadata surfaces."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from api.db import workspace_db_conn as db_conn


def _asset(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": str(row[0]),
        "filename": row[1],
        "mediaType": row[2],
        "byteSize": int(row[3]),
        "sha256": row[4],
        "status": row[5],
        "visibility": row[6],
        "version": int(row[7]),
        "updatedAt": row[8].isoformat() if hasattr(row[8], "isoformat") else row[8],
    }


class PostgresMediaLibraryRepository:
    """Every query carries site scope; callers never provide storage keys."""

    def list_assets(
        self,
        *,
        site_id: str,
        limit: int,
        offset: int,
        state: str | None = None,
        media_type: str | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        clauses = ["site_id=%s", "status<>'purged'"]
        params: list[Any] = [site_id]
        if state:
            clauses.append("status=%s")
            params.append(state)
        if media_type:
            clauses.append("media_type=%s")
            params.append(media_type)
        if search:
            clauses.append("original_name ILIKE %s")
            params.append(f"%{search}%")
        where = " AND ".join(clauses)
        with db_conn(tenant_id=site_id) as conn, conn.cursor() as cur:
            cur.execute(
                f"""SELECT id, original_name, media_type, byte_size, sha256, status,
                            visibility, lock_version, updated_at
                     FROM sitecontent_mediaasset
                     WHERE {where}
                     ORDER BY updated_at DESC, id DESC LIMIT %s OFFSET %s""",
                (*params, limit + 1, offset),
            )
            rows = cur.fetchall()
        more = len(rows) > limit
        return {
            "items": [_asset(row) for row in rows[:limit]],
            "nextOffset": offset + limit if more else None,
            "indexStatus": "current",
        }

    def get_asset(self, *, site_id: str, asset_id: UUID) -> dict[str, Any]:
        with db_conn(tenant_id=site_id) as conn, conn.cursor() as cur:
            cur.execute(
                """SELECT id, original_name, media_type, byte_size, sha256, status,
                          visibility, lock_version, updated_at
                   FROM sitecontent_mediaasset
                   WHERE site_id=%s AND id=%s AND status<>'purged'""",
                (site_id, str(asset_id)),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError("media_not_found")
            cur.execute(
                """SELECT name, media_type, byte_size, sha256, width, height,
                          recipe_id, recipe_version, inline_safe
                   FROM sitecontent_mediavariant
                   WHERE asset_id=%s ORDER BY name""",
                (str(asset_id),),
            )
            variants = cur.fetchall()
        result = _asset(row)
        result["variants"] = [
            {
                "name": item[0],
                "mediaType": item[1],
                "byteSize": int(item[2]),
                "sha256": item[3],
                "width": item[4],
                "height": item[5],
                "recipeId": item[6],
                "recipeVersion": int(item[7]),
                "inlineSafe": bool(item[8]),
            }
            for item in variants
        ]
        return result

    def update_metadata(
        self,
        *,
        site_id: str,
        asset_id: UUID,
        actor_ref: str,
        expected_version: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        with db_conn(tenant_id=site_id) as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """SELECT lock_version, media_type FROM sitecontent_mediaasset
                           WHERE site_id=%s AND id=%s AND status NOT IN ('purged','soft_deleted')
                           FOR UPDATE""",
                        (site_id, str(asset_id)),
                    )
                    current = cur.fetchone()
                    if not current:
                        raise ValueError("media_not_found")
                    if int(current[0]) != expected_version:
                        raise ValueError("media_version_conflict")
                    decorative = bool(payload["decorative"])
                    if current[1].startswith("image/") and not decorative and not payload["altText"].strip():
                        raise ValueError("media_alt_or_decorative_required")
                    cur.execute(
                        """SELECT COALESCE(MAX(revision),0)+1
                           FROM sitecontent_mediametadatarevision
                           WHERE site_id=%s AND asset_id=%s AND locale=%s""",
                        (site_id, str(asset_id), payload["locale"]),
                    )
                    revision = int(cur.fetchone()[0])
                    cur.execute(
                        """INSERT INTO sitecontent_mediametadatarevision
                           (id, site_id, asset_id, revision, locale, alt_text, decorative,
                            caption, credit, license_code, focal_x, focal_y, actor_ref,
                            created_at, updated_at)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NOW())""",
                        (
                            str(uuid4()), site_id, str(asset_id), revision, payload["locale"],
                            payload["altText"], decorative, payload["caption"], payload["credit"],
                            payload["licenseCode"], payload["focalX"], payload["focalY"], actor_ref,
                        ),
                    )
                    cur.execute(
                        """UPDATE sitecontent_mediaasset
                           SET visibility=%s, lock_version=lock_version+1, updated_at=NOW()
                           WHERE site_id=%s AND id=%s AND lock_version=%s
                           RETURNING lock_version""",
                        (payload["visibility"], site_id, str(asset_id), expected_version),
                    )
                    next_version = int(cur.fetchone()[0])
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return {"id": str(asset_id), "revision": revision, "version": next_version}
