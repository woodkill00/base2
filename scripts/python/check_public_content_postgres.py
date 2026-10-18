"""Actual restricted-role regressions, invoked by disposable PostgreSQL acceptance."""

from unittest.mock import patch
from uuid import uuid4

from psycopg2 import errors

from api import db
from api.repositories.site_content import PostgresSiteContentRepository


def check(owner, pool_context, user, password):
    repo = PostgresSiteContentRepository()
    tenant = "public-content-acceptance"
    other = "public-content-other"
    ids = [str(uuid4()) for _ in range(4)]
    media = [str(uuid4()) for _ in range(3)]
    with owner, owner.cursor() as cur:
        for record_id, site, state in zip(
            ids,
            [tenant, tenant, other, tenant],
            ["published", "draft", "published", "archived"],
            strict=False,
        ):
            cur.execute(
                """INSERT INTO sitecontent_contentrecord
                (id,site_id,content_type,slug,title,excerpt,body,metadata,state,
                 schedule_timezone,sitemap_include,search_visible,version,schema_version,
                 values,created_at,updated_at)
                VALUES (%s,%s,'page',%s,'Public test','','Body','{}',%s,'',true,true,1,1,
                        '{}',NOW(),NOW())""",
                (record_id, site, record_id, state),
            )
            cur.execute(
                """INSERT INTO sitecontent_searchdocument
                (id,site_id,content_id,title,body,url_path,visibility,indexed_at,
                 source_updated_at,created_at,updated_at)
                VALUES (%s,%s,%s,'Public test','Body','/about','public',NOW(),NOW(),NOW(),NOW())""",
                (str(uuid4()), site, record_id),
            )
        for asset_id, visibility, status in zip(
            media,
            ["public", "private", "public"],
            ["validated", "validated", "quarantined"],
            strict=False,
        ):
            cur.execute(
                """INSERT INTO sitecontent_mediaasset
                (id,site_id,storage_key,original_name,media_type,byte_size,sha256,status,
                 owner_ref,attribution,metadata,visibility,lock_version,current_object_version,
                 authorization_epoch,created_at,updated_at)
                VALUES (%s,%s,%s,'test.png','image/png',10,%s,%s,'owner','','{}',%s,
                        1,1,1,NOW(),NOW())""",
                (asset_id, tenant, asset_id, "a" * 64, status, visibility),
            )
    try:
        with pool_context(user, password):
            assert repo.get_content(site_id=tenant, content_type="page", slug=ids[0])
            for record_id in ids[1:]:
                assert repo.get_content(site_id=tenant, content_type="page", slug=record_id) is None
            assert len(repo.list_content(site_id=tenant, limit=10, cursor=None)["items"]) == 1
            assert (
                len(repo.search(site_id=tenant, query="Public", limit=10, cursor=None)["items"])
                == 1
            )
            assert repo.get_media(site_id=tenant, asset_id=media[0])
            assert repo.get_media(site_id=other, asset_id=media[0]) is None
            for asset_id in media[1:]:
                assert repo.get_media(site_id=tenant, asset_id=asset_id) is None
            # Direct SQL must not bypass the repository's published/tenant predicates.
            with db.db_conn(tenant_id=tenant) as conn, conn.cursor() as cur:
                cur.execute("SELECT id FROM sitecontent_contentrecord")
                assert [str(row[0]) for row in cur.fetchall()] == [ids[0]]
            with db.db_conn() as conn, conn.cursor() as cur:
                cur.execute("SELECT id FROM sitecontent_contentrecord")
                assert cur.fetchall() == []  # Pool reset must remove the preceding tenant.
            # Exercise the exact optional pack types used by the browser, with
            # publication changes in real storage rather than route mocks.
            for content_type in ("blog-post", "portfolio-item", "doc-page"):
                with owner, owner.cursor() as cur:
                    cur.execute(
                        "UPDATE sitecontent_contentrecord SET content_type=%s "
                        "WHERE id=ANY(%s::uuid[])",
                        (content_type, ids),
                    )
                assert repo.get_content(site_id=tenant, content_type=content_type, slug=ids[0])
                assert (
                    repo.get_content(site_id=other, content_type=content_type, slug=ids[0]) is None
                )
                assert (
                    repo.get_content(site_id=tenant, content_type=content_type, slug=ids[1]) is None
                )
                assert (
                    len(
                        repo.list_content(
                            site_id=tenant, limit=10, cursor=None, content_type=content_type
                        )["items"]
                    )
                    == 1
                )
                assert (
                    repo.list_content(site_id=tenant, limit=10, cursor=None, content_type="page")[
                        "items"
                    ]
                    == []
                )
                with owner, owner.cursor() as cur:
                    cur.execute(
                        "UPDATE sitecontent_contentrecord SET state='published' WHERE id=%s",
                        (ids[1],),
                    )
                assert (
                    len(
                        repo.list_content(
                            site_id=tenant, limit=10, cursor=None, content_type=content_type
                        )["items"]
                    )
                    == 2
                )
                with owner, owner.cursor() as cur:
                    cur.execute(
                        "UPDATE sitecontent_contentrecord SET state='archived' WHERE id=%s",
                        (ids[0],),
                    )
                assert (
                    repo.get_content(site_id=tenant, content_type=content_type, slug=ids[0]) is None
                )
                with owner, owner.cursor() as cur:
                    cur.execute(
                        "UPDATE sitecontent_contentrecord SET state='published' WHERE id=%s",
                        (ids[0],),
                    )
                    cur.execute(
                        "UPDATE sitecontent_contentrecord SET state='draft' WHERE id=%s", (ids[1],)
                    )
            for sql in (
                "UPDATE sitecontent_contentrecord SET title=title",
                "DELETE FROM sitecontent_contentrecord",
                "SELECT storage_key FROM sitecontent_mediaasset",
                "SELECT payload FROM sitecontent_formsubmission",
                "SELECT * FROM sitecontent_formdeliveryoutbox",
            ):
                try:
                    with db.db_conn(tenant_id=tenant) as conn, conn.cursor() as cur:
                        cur.execute(sql)
                except errors.InsufficientPrivilege:
                    pass
                else:
                    raise AssertionError("public_content_excess_privilege:" + sql)
            draft = repo.create_community_post(
                site_id=tenant,
                author_ref="synthetic",
                payload={"title": "Review me", "body": "Safe body", "abuseScore": 0},
            )
            assert (
                repo.get_content(site_id=tenant, content_type="community-post", slug=draft["slug"])
                is None
            )
            # A mismatched caller-supplied site cannot escape the bound tenant.
            with patch(
                "api.repositories.site_content.db_conn",
                lambda **kwargs: db.db_conn(tenant_id=tenant),
            ):
                try:
                    repo.create_community_post(
                        site_id=other,
                        author_ref="synthetic",
                        payload={"title": "Denied", "body": "Safe", "abuseScore": 0},
                    )
                except errors.InsufficientPrivilege:
                    pass
                else:
                    raise AssertionError("cross_tenant_community_write_allowed")
            args = dict(
                site_id=tenant,
                form_key="contact",
                replay_key="synthetic-replay",
                payload={"message": "test"},
                consent={"processing": True},
                request_id="test",
                retention_days=7,
                request_digest="a" * 64,
            )
            receipt = repo.submit_form(**args)
            replay = repo.submit_form(**args)
            assert str(receipt["id"]) == str(replay["id"]) and replay["replayed"]
            forbidden_writes = [
                (
                    """INSERT INTO sitecontent_contentrecord
                    (id,site_id,content_type,slug,title,excerpt,body,metadata,state,
                     sitemap_include,search_visible,version,schedule_timezone,schema_version,
                     values,created_at,updated_at)
                    VALUES (%s,%s,'community-post','denied','Denied','','','{}','published',
                            FALSE,FALSE,1,'',1,'{}',NOW(),NOW())""",
                    (str(uuid4()), tenant),
                ),
                (
                    """INSERT INTO sitecontent_formdeliveryoutbox
                    (id,submission_id,adapter,status,attempts,next_attempt_at,last_error_code,
                     created_at,updated_at)
                    VALUES (%s,%s,'external','queued',0,NOW(),'',NOW(),NOW())""",
                    (str(uuid4()), str(receipt["id"])),
                ),
            ]
            for sql, params in forbidden_writes:
                try:
                    with db.db_conn(tenant_id=tenant) as conn, conn.cursor() as cur:
                        cur.execute(sql, params)
                except errors.InsufficientPrivilege:
                    pass
                else:
                    raise AssertionError("public_content_unsafe_write_allowed")
            with patch(
                "api.repositories.site_content.db_conn",
                lambda **kwargs: db.db_conn(tenant_id=tenant),
            ):
                try:
                    repo.submit_form(**dict(args, site_id=other))
                except errors.InsufficientPrivilege:
                    pass
                else:
                    raise AssertionError("cross_tenant_form_write_allowed")
            try:
                repo.submit_form(**dict(args, request_digest="b" * 64))
            except ValueError as exc:
                assert str(exc) == "idempotency_conflict"
            else:
                raise AssertionError("form_replay_conflict_not_rejected")
            with db.db_conn(tenant_id=other) as conn, conn.cursor() as cur:
                cur.execute("SELECT id FROM sitecontent_formsubmission")
                assert cur.fetchall() == []
        with owner, owner.cursor() as cur:
            cur.execute(
                "SELECT adapter,status FROM sitecontent_formdeliveryoutbox WHERE submission_id=%s",
                (str(receipt["id"]),),
            )
            assert cur.fetchone() == ("disabled", "queued")
    finally:
        with owner, owner.cursor() as cur:
            cur.execute(
                "DELETE FROM sitecontent_formdeliveryoutbox WHERE submission_id IN "
                "(SELECT id FROM sitecontent_formsubmission WHERE site_id=%s)",
                (tenant,),
            )
            cur.execute("DELETE FROM sitecontent_formsubmission WHERE site_id=%s", (tenant,))
            cur.execute(
                "DELETE FROM sitecontent_searchdocument WHERE site_id IN (%s,%s)", (tenant, other)
            )
            cur.execute(
                "DELETE FROM sitecontent_contentrecord WHERE site_id IN (%s,%s)", (tenant, other)
            )
            cur.execute("DELETE FROM sitecontent_mediaasset WHERE site_id=%s", (tenant,))
    print("Public content restricted-role acceptance: PASS")
