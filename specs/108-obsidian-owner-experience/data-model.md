# Data and state

Reuse canonical user, tenant/membership, preference and audit models. Any necessary
schema change starts in Django and requires migration and runtime-role tests.

Private configuration: enabled=false by default, exact environment/profile,
display name, email, tenant, credential reference, minimum application role.
Do not commit real email/password as a reusable template default.

Provisioning states: disabled → preflight → created | existing-preserved | blocked.
Missing secrets, identity/tenant conflicts or inactive existing owner block safely.
existing-preserved cannot mutate security state. Concurrent creation re-reads the
unique identity transactionally. Rotation is a separate explicit action.

Evidence: schema version, source commit, route/state/viewport/profile, synthetic
fixture ID, outcome, screenshot digest, test receipt and human baseline approval.
No credentials or real owner details appear in public artifacts.

Fresh DB: configured login recreated, new DB identity, no old data.
Retained DB: same identity/data/security retained. Restore is a distinct operation.
