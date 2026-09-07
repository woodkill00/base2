# Implementation plan

1. Extend the closed module catalog and generated reference profile; prove
   disabled profiles retain no surface.
2. Add tenant-owned Django entities and PostgreSQL forced-RLS migration.
3. Add pure policy, lifecycle, quota, grants, format, and processor contracts.
4. Reuse Feature 104 encrypted storage, attachment, audit, and worker paths,
   extending them without introducing a second authorization model.
5. Register the FastAPI media router only for enabled profiles and expose only
   bounded versioned contracts.
6. Add the accessible React library and generated navigation.
7. Run focused, full-stack, security, migration, browser, visual, generator,
   secret, dependency, and repeated-state tests.
8. After separate approval, publish a draft PR; require hosted review before a
   separately approved merge. A staging-only canary and its teardown require
   another approval.

Rollback is code rollback plus a compatibility-preserving forward migration;
stored objects are never deleted by code rollback. Capability disable preserves
data while removing navigation, routes, jobs, and allocation authority.
