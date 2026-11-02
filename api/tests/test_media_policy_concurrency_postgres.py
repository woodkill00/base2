"""Real row-lock lease regression; supported disposable PostgreSQL runner only."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import monotonic, sleep
from uuid import uuid4

import pytest

from api.db import workspace_worker_db_conn
from api.services.media_library_runtime import _owns_inspection_claim

pytestmark = pytest.mark.integration


def test_unchanged_job_lock_wait_cannot_extend_expired_claim(workspace_policy_fixture):
    f = workspace_policy_fixture
    site, asset, job, digest = f['site_id'], uuid4(), uuid4(), 'a' * 64
    f['execute']("""INSERT INTO sitecontent_mediaasset
        (id,site_id,storage_key,original_name,media_type,byte_size,sha256,status,
         owner_ref,attribution,metadata,visibility,lock_version,current_object_version,
         authorization_epoch,created_at,updated_at)
        VALUES (%s,%s,%s,'synthetic.png','image/png',1,%s,'quarantined',
                'system:test','','{}','private',1,1,1,NOW(),NOW())""",
        (str(asset), site, f'media/{site}/{asset}.bin', digest))
    token = f['execute']("""INSERT INTO sitecontent_mediajob
        (id,site_id,asset_id,kind,status,idempotency_key,request_digest,attempt,
         maximum_attempts,error_code,output_digest,available_at,lease_expires_at,
         created_at,updated_at)
        VALUES (%s,%s,%s,'inspect','running',%s,%s,0,3,'','',NOW(),
                clock_timestamp()+INTERVAL '3 seconds',NOW(),NOW())
        RETURNING lease_expires_at""",
        (str(job), site, str(asset), f'inspect:{asset}:1', digest))[0][0]
    row = ('unused', digest, 'quarantined', 'image/png', 1, 1, 1)
    started, worker_pid = Event(), []

    def check_claim():
        with workspace_worker_db_conn(tenant_id=site) as conn, conn.cursor() as cur:
            cur.execute("SET LOCAL statement_timeout='10s'")
            cur.execute('SELECT pg_backend_pid()')
            worker_pid.append(cur.fetchone()[0])
            started.set()
            return _owns_inspection_claim(cur, site_id=site, asset_id=asset,
                job_id=job, attempt=1, lease_token=token, row=row)

    # Hold the row unchanged: PostgreSQL need not re-evaluate its pre-lock WHERE
    # predicate when granting this lock after the deadline.
    with workspace_worker_db_conn(tenant_id=site) as holder, holder.cursor() as cur:
        cur.execute('SELECT id FROM sitecontent_mediajob WHERE id=%s FOR UPDATE', (str(job),))
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(check_claim)
            try:
                assert started.wait(5)
                deadline = monotonic() + 5
                while not f['execute']('SELECT cardinality(pg_blocking_pids(%s))', (worker_pid[0],))[0][0]:
                    assert monotonic() < deadline, 'claim did not enter its row-lock wait'
                    sleep(0.01)
                f['execute']('SELECT pg_sleep(GREATEST(0, EXTRACT(EPOCH FROM (%s-clock_timestamp())))+0.05)', (token,))
            finally:
                holder.rollback()
            assert pending.result(timeout=5) is False
