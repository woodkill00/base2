"""Explicit, replay-safe lifecycle bootstrap for the disposable Base2 preview only."""

import json
import os
from uuid import NAMESPACE_URL, uuid5

from api.repositories import tenant_lifecycle as repository
from api.services.tenant_lifecycle import persist_transition

PROFILE = 'base2-obsidian'
OWNER = 'base2-preview-operator'
CONFIGURATION = {'purpose': 'disposable-full-preview'}
PROVISION_ID = uuid5(NAMESPACE_URL, 'base2/full-preview/lifecycle/provision/v1')
ACTIVATE_ID = uuid5(NAMESPACE_URL, 'base2/full-preview/lifecycle/activate/v1')


def ensure(*, enabled: bool, profile: str) -> dict:
    if not enabled:
        return {'status': 'disabled'}
    if profile != PROFILE:
        raise ValueError('preview_lifecycle_profile_denied')
    try:
        state = repository.get_state(tenant_id=PROFILE)
    except repository.TenantLifecycleRepositoryError as exc:
        if str(exc) != 'tenant:lifecycle_missing':
            raise
        state = repository.provision(
            tenant_id=PROFILE,
            owner_ref=OWNER,
            operation_id=PROVISION_ID,
            configuration=CONFIGURATION,
        )
    if state['owner'] != OWNER or state['configuration'] != CONFIGURATION:
        raise ValueError('preview_lifecycle_ownership_conflict')
    if state['state'] == 'active':
        if state['operationId'] != str(ACTIVATE_ID) or state['revision'] != 2:
            raise ValueError('preview_lifecycle_revision_conflict')
        return {'status': 'active', 'created': False}
    if (
        state['state'] != 'provisioning'
        or state['operationId'] != str(PROVISION_ID)
        or state['revision'] != 1
    ):
        raise ValueError('preview_lifecycle_transition_denied')
    activated = persist_transition(
        tenant_id=PROFILE,
        target='active',
        owner=OWNER,
        expected_revision=1,
        operation_id=ACTIVATE_ID,
    )
    if activated['state'] != 'active':
        raise ValueError('preview_lifecycle_activation_failed')
    return {'status': 'active', 'created': True}


def main() -> int:
    try:
        result = ensure(
            enabled=os.environ.get('BASE2_PREVIEW_LIFECYCLE_ENABLED') == 'true',
            profile=os.environ.get('SITE_PROFILE', ''),
        )
    except Exception:
        print(json.dumps({'status': 'failed', 'error': 'preview_lifecycle_bootstrap_failed'}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
