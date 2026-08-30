from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from api.db import db_conn


def _content(row) -> dict[str, Any]:
    return {
        'id': row[0],
        'contentType': row[1],
        'slug': row[2],
        'title': row[3],
        'excerpt': row[4],
        'body': row[5],
        'metadata': row[6],
        'publishedAt': row[7],
        'updatedAt': row[8],
    }


class PostgresSiteContentRepository:
    def create_community_post(self, *, site_id: str, author_ref: str, payload: dict[str, Any]):
        record_id, now = uuid4(), datetime.now(UTC)
        slug = f'post-{record_id.hex[:16]}'
        with db_conn(tenant_id=site_id) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO sitecontent_contentrecord
                       (id,site_id,content_type,slug,title,excerpt,body,metadata,state,
                        sitemap_include,search_visible,version,created_at,updated_at)
                       VALUES (%s,%s,'community-post',%s,%s,'',%s,%s,'draft',FALSE,FALSE,1,%s,%s)""",
                    (str(record_id),site_id,slug,payload['title'],payload['body'],
                     json.dumps({'authorRef':author_ref,'moderationStatus':'pending',
                                 'abuseScore':payload['abuseScore']}),now,now),
                )
            conn.commit()
        return {'id':record_id,'slug':slug,'moderationStatus':'pending'}

    def list_content(
        self, *, site_id: str, limit: int, cursor: UUID | None, content_type: str | None = None
    ):
        clauses = []
        params: list[str | int] = [site_id]
        if content_type:
            clauses.append('AND content_type=%s')
            params.append(content_type)
        if cursor:
            clauses.append('AND id < %s')
            params.append(str(cursor))
        clause = ' '.join(clauses)
        params.append(limit + 1)
        with db_conn(tenant_id=site_id) as conn, conn.cursor() as cur:
            cur.execute(
                f"""SELECT id, content_type, slug, title, excerpt, body, metadata,
                           published_at, updated_at
                    FROM sitecontent_contentrecord
                    WHERE site_id=%s AND state='published' AND search_visible=TRUE {clause}
                    ORDER BY id DESC LIMIT %s""",
                tuple(params),
            )
            rows = cur.fetchall()
        items = [_content(row) for row in rows[:limit]]
        return {'items': items, 'nextCursor': str(items[-1]['id']) if len(rows) > limit else None}

    def get_content(self, *, site_id: str, content_type: str, slug: str):
        with db_conn(tenant_id=site_id) as conn, conn.cursor() as cur:
            cur.execute(
                """SELECT id, content_type, slug, title, excerpt, body, metadata,
                          published_at, updated_at
                   FROM sitecontent_contentrecord
                   WHERE site_id=%s AND content_type=%s AND slug=%s AND state='published'""",
                (site_id, content_type, slug),
            )
            row = cur.fetchone()
        return _content(row) if row else None

    def get_media(self, *, site_id: str, asset_id: UUID):
        with db_conn(tenant_id=site_id) as conn, conn.cursor() as cur:
            cur.execute(
                """SELECT id, original_name, media_type, byte_size, sha256, attribution, metadata, updated_at
                   FROM sitecontent_mediaasset
                   WHERE site_id=%s AND id=%s AND status='validated'""",
                (site_id, str(asset_id)),
            )
            row = cur.fetchone()
        if not row:
            return None
        return {
            'id': row[0],
            'name': row[1],
            'mediaType': row[2],
            'byteSize': row[3],
            'sha256': row[4],
            'attribution': row[5],
            'metadata': row[6],
            'updatedAt': row[7],
        }

    def search(self, *, site_id: str, query: str, limit: int, cursor: UUID | None):
        clause = 'AND d.id < %s' if cursor else ''
        params: list[str | int] = [site_id, f'%{query}%', f'%{query}%']
        if cursor:
            params.append(str(cursor))
        params.append(limit + 1)
        with db_conn(tenant_id=site_id) as conn, conn.cursor() as cur:
            cur.execute(
                f"""SELECT d.id, d.title, d.body, d.url_path, d.indexed_at, d.source_updated_at
                    FROM sitecontent_searchdocument d
                    JOIN sitecontent_contentrecord c ON c.id=d.content_id AND c.site_id=d.site_id
                    WHERE d.site_id=%s AND d.visibility='public' AND d.tombstoned_at IS NULL
                      AND c.state='published' AND c.search_visible=TRUE
                      AND (d.title ILIKE %s OR d.body ILIKE %s) {clause}
                    ORDER BY d.id DESC LIMIT %s""",
                tuple(params),
            )
            rows = cur.fetchall()
        items = [
            {
                'id': row[0],
                'title': row[1],
                'excerpt': row[2][:320],
                'urlPath': row[3],
                'indexedAt': row[4],
            }
            for row in rows[:limit]
        ]
        fresh = min((row[5] for row in rows[:limit]), default=datetime.now(UTC))
        return {
            'items': items,
            'nextCursor': str(items[-1]['id']) if len(rows) > limit else None,
            'freshThrough': fresh,
        }

    def submit_form(
        self,
        *,
        site_id,
        form_key,
        replay_key,
        payload,
        consent,
        request_id,
        retention_days,
        request_digest,
    ):
        now = datetime.now(UTC)
        with db_conn(tenant_id=site_id) as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """SELECT id, status, created_at, request_digest FROM sitecontent_formsubmission
                           WHERE site_id=%s AND form_key=%s AND replay_key=%s""",
                        (site_id, form_key, replay_key),
                    )
                    existing = cur.fetchone()
                    if existing:
                        conn.rollback()
                        if existing[3] != request_digest:
                            raise ValueError('idempotency_conflict')
                        return {
                            'id': existing[0],
                            'status': existing[1],
                            'replayed': True,
                            'receivedAt': existing[2],
                        }
                    submission_id, delivery_id = uuid4(), uuid4()
                    cur.execute(
                        """INSERT INTO sitecontent_formsubmission
                           (id, site_id, form_key, replay_key, request_digest, payload, consent, request_id, status,
                            retained_until, created_at, updated_at)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'queued',%s,%s,%s)""",
                        (
                            str(submission_id),
                            site_id,
                            form_key,
                            replay_key,
                            request_digest,
                            json.dumps(payload),
                            json.dumps(consent),
                            request_id,
                            now + timedelta(days=retention_days),
                            now,
                            now,
                        ),
                    )
                    cur.execute(
                        """INSERT INTO sitecontent_formdeliveryoutbox
                           (id, submission_id, adapter, status, attempts, next_attempt_at,
                            last_error_code, created_at, updated_at)
                           VALUES (%s,%s,'disabled','queued',0,%s,'',%s,%s)""",
                        (str(delivery_id), str(submission_id), now, now, now),
                    )
                conn.commit()
                return {
                    'id': submission_id,
                    'status': 'queued',
                    'replayed': False,
                    'receivedAt': now,
                }
            except Exception:
                conn.rollback()
                raise
