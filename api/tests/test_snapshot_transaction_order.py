from types import SimpleNamespace

import pytest

from api import db


@pytest.mark.parametrize('fail_binding', [False, True])
def test_snapshot_options_precede_rls_binding_and_cleanup_is_unconditional(
    monkeypatch, fail_binding
):
    calls = []
    connection = SimpleNamespace(set_session=lambda **kw: calls.append(('options', kw)))
    pool = SimpleNamespace(putconn=lambda conn: calls.append(('returned', conn is connection)))
    monkeypatch.setattr(db, '_get_conn', lambda: connection)
    monkeypatch.setattr(db, '_get_pool', lambda: pool)

    def bind(conn, tenant):
        calls.append(('tenant', tenant))
        if fail_binding:
            raise RuntimeError('synthetic_binding_failure')

    monkeypatch.setattr(db, '_bind_tenant', bind)
    monkeypatch.setattr(db, '_bind_data_rights_claim', lambda conn: calls.append(('claim', True)))
    monkeypatch.setattr(db, '_reset_connection', lambda conn: calls.append(('reset', True)))
    if fail_binding:
        with (
            pytest.raises(RuntimeError, match='synthetic_binding_failure'),
            db.db_conn(tenant_id='tenant-a', isolation_level='REPEATABLE READ', readonly=True),
        ):
            pytest.fail('must not yield a connection after binding failure')
    else:
        with db.db_conn(
            tenant_id='tenant-a', isolation_level='REPEATABLE READ', readonly=True
        ) as actual:
            assert actual is connection
            calls.append(('yielded', True))
    assert calls[:2] == [
        ('options', {'isolation_level': 'REPEATABLE READ', 'readonly': True}),
        ('tenant', 'tenant-a'),
    ]
    assert calls[-2:] == [('reset', True), ('returned', True)]
    assert ('claim', True) in calls if not fail_binding else ('claim', True) not in calls


def test_default_connection_does_not_change_transaction_options(monkeypatch):
    connection = SimpleNamespace()
    monkeypatch.setattr(db, '_get_conn', lambda: connection)
    monkeypatch.setattr(db, '_get_pool', lambda: SimpleNamespace(putconn=lambda conn: None))
    monkeypatch.setattr(db, '_bind_data_rights_claim', lambda conn: None)
    monkeypatch.setattr(db, '_reset_connection', lambda conn: None)
    with db.db_conn() as actual:
        assert actual is connection
