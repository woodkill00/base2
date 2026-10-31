const { test, expect } = require('@playwright/test');
const { execFileSync } = require('node:child_process');
const path = require('node:path');

// No route interception, session injection, storage tokens, tenant selector, or
// test-support HTTP controls. Credentials belong only to this fresh Compose DB.
const SITE = 'base2-obsidian';
const PASSWORD = 'SyntheticE2e124!Password';
const ROOT = path.resolve(__dirname, '../..');
const COMPOSE = [
  'compose',
  '-p',
  'base2-e2e-isolated',
  '-f',
  path.join(ROOT, 'e2e/docker-compose.e2e.yml'),
];
const BASE = process.env.E2E_BASE_URL || 'http://127.0.0.1:18080';
const TYPE = 'acceptancearticle';
const RECORDS = `/content/v1/types/${TYPE}/records`;
let detachedControl = false;

function compose(...args) {
  return execFileSync('docker', [...COMPOSE, ...args], {
    cwd: ROOT,
    encoding: 'utf8',
    timeout: 60_000,
    stdio: ['ignore', 'pipe', 'pipe'],
  });
}
function resumeService(service) {
  if (!['celery-content-worker', 'celery-beat'].includes(service)) {
    throw new Error('Only existing acceptance workers may be resumed');
  }
  // `start` traverses completed dependencies and would rerun the one-shot seed.
  // Compose up supports no-deps; do not invent a start --no-deps option.
  return compose(
    'up',
    '-d',
    '--no-deps',
    '--no-build',
    '--no-recreate',
    '--pull',
    'never',
    service
  );
}

function control(command, now) {
  const args = [
    ...(detachedControl ? ['run', '--rm', '--no-deps', '-T'] : ['exec', '-T']),
    'celery-content-worker',
    'python',
    '/e2e-support/workspace_fixture.py',
    command,
  ];
  if (now) args.push('--now', now);
  return JSON.parse(compose(...args));
}
const snapshot = () => control('snapshot');
const consume = (now = new Date(Date.now() + 1000).toISOString()) => control('consume', now);

async function login(browser, identity) {
  const context = await browser.newContext();
  const page = await context.newPage();
  await page.goto(`${BASE}/login`);
  await page.getByLabel('Email', { exact: true }).fill(identity.email);
  await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
  let loggedIn;
  for (let attempt = 0; attempt < 2; attempt += 1) {
    const response = page.waitForResponse(
      (r) => r.url().endsWith('/api/auth/login') && r.request().method() === 'POST'
    );
    await page.getByRole('button', { name: 'Sign in', exact: true }).click();
    loggedIn = await response;
    if (loggedIn.status() !== 429) break;
    // All synthetic actors share the Nginx IP. Respect the real limiter, do not
    // disable it or retry authentication failures. The trace retains the 429.
    const retry = Number(loggedIn.headers()['retry-after']);
    expect(Number.isFinite(retry) && retry > 0 && retry <= 61).toBe(true);
    if (attempt === 0) await new Promise((resolve) => setTimeout(resolve, (retry + 1) * 1000));
  }
  expect(loggedIn.status()).toBe(200);
  const { access_token: token } = await loggedIn.json();
  expect(token).toBeTruthy();
  await expect(page).toHaveURL(/\/dashboard$/);
  const cookies = await context.cookies();
  expect(cookies.find((c) => c.name.endsWith('_refresh'))?.httpOnly).toBe(true);
  expect(cookies.find((c) => c.name.endsWith('_csrf'))).toBeTruthy();
  return { context, page, token, ...identity };
}
async function api(actor, method, route, data, status = 200, extraHeaders = {}) {
  const csrf = (await actor.context.cookies()).find((cookie) =>
    cookie.name.endsWith('_csrf')
  )?.value;
  const result = await actor.context.request.fetch(`${BASE}/api${route}`, {
    method,
    data,
    headers: {
      Authorization: `Bearer ${actor.token}`,
      'X-Tenant-Id': SITE,
      ...(csrf ? { 'X-CSRF-Token': csrf } : {}),
      ...extraHeaders,
    },
  });
  expect(result.status(), `${method} ${route}: ${await result.text()}`).toBe(status);
  return result.headers()['content-type']?.includes('application/json')
    ? result.json()
    : result.body();
}
async function policy(actor, requireReview, publicAccess) {
  const previous = await api(actor, 'GET', '/settings/workspace-policy');
  return api(actor, 'PUT', '/settings/workspace-policy', {
    expected_version: previous.version,
    require_review: requireReview,
    public_access: publicAccess,
  });
}
async function preference(actor, delivery) {
  const previous = await api(actor, 'GET', '/settings/notifications');
  return api(actor, 'PUT', '/settings/notifications', {
    expected_version: previous.version,
    preferences: [{ event_family: 'product', channel: 'email', delivery }],
  });
}
async function record(actor, slug) {
  return api(
    actor,
    'POST',
    RECORDS,
    { title: `Acceptance ${slug}`, slug, values: { summary: slug } },
    201
  );
}
async function read(actor, item) {
  return api(actor, 'GET', `${RECORDS}/${item.id}`);
}
async function transition(actor, item, action, status = 200, additional = {}) {
  return api(
    actor,
    'POST',
    `${RECORDS}/${item.id}/transitions/${action}`,
    { expectedVersion: item.version, ...additional },
    status
  );
}
async function approve(actor, item, status = 200) {
  return api(
    actor,
    'POST',
    `${RECORDS}/${item.id}/review-approval`,
    { expectedVersion: item.version },
    status
  );
}
async function role(owner, member, value) {
  // Role management requires a recent password authentication, not a refreshed
  // session. Use the real login endpoint rather than relaxing its 5-minute rule.
  const authenticated = await api(owner, 'POST', '/auth/login', {
    email: owner.email,
    password: PASSWORD,
  });
  owner.token = authenticated.access_token;
  const overview = await api(owner, 'GET', '/admin/overview');
  const current = overview.members.find((m) => m.id === member.id);
  expect(current).toBeTruthy();
  await api(owner, 'PATCH', `/admin/members/${member.id}/role`, {
    role: value,
    expected_updated_at: current.updated_at,
  });
}
function intentFor(state, item, actor) {
  return state.intents.find((i) => i.recordId === item.id && i.recipientId === actor.id);
}

// One ordered, non-retried journey owns the shared policy and disposable seed.
// A retry must get a fresh stack, never conceal partial state from a first failure.
test.describe('Feature124 real browser/API/PostgreSQL workspace acceptance', () => {
  test.describe.configure({ mode: 'serial', retries: 0 });
  test('CAS, independent review, synchronous visibility and durable local delivery', async ({
    browser,
  }, testInfo) => {
    test.setTimeout(600_000);
    const seeded = snapshot();
    expect(seeded.site).toBe(SITE);
    expect(seeded.databaseRole).toBe('base2_workspace_worker_e2e');
    const actors = {};
    let beatStopped = false;
    let primaryFailure;
    try {
      for (const name of Object.keys(seeded.actors))
        actors[name] = await login(browser, seeded.actors[name]);
      const { owner, editor, reviewer, viewer, suspended, outsider } = actors;
      await test.step('real cookie refresh requires CSRF; two live tabs cannot overwrite preferences', async () => {
        const denied = await reviewer.context.request.post(`${BASE}/api/auth/refresh`, {
          data: {},
        });
        expect(denied.status()).toBe(403);
        const first = reviewer.page;
        const second = await reviewer.context.newPage();
        await first.goto(`${BASE}/settings/notifications`);
        await second.goto(`${BASE}/settings/notifications`);
        const label = 'Product Email delivery';
        await expect(first.getByLabel(label, { exact: true })).toBeVisible();
        await expect(second.getByLabel(label, { exact: true })).toBeVisible();
        await first.getByLabel(label, { exact: true }).selectOption('immediate');
        await second.getByLabel(label, { exact: true }).selectOption('digest');
        await first.getByRole('button', { name: 'Save notifications', exact: true }).click();
        await expect(
          first
            .locator('div[role="status"]')
            .filter({ hasText: /^Notification preferences saved\.$/ })
        ).toBeVisible();
        const conflict = second.waitForResponse(
          (r) => r.url().endsWith('/api/settings/notifications') && r.request().method() === 'PUT'
        );
        await second.getByRole('button', { name: 'Save notifications', exact: true }).click();
        expect((await conflict).status()).toBe(409);
        await expect(second.getByLabel(label, { exact: true })).toHaveValue('digest');
        await second
          .getByRole('button', { name: 'Discard draft and reload notifications', exact: true })
          .click();
        await expect(second.getByLabel(label, { exact: true })).toHaveValue('immediate');
        await second.reload();
        await expect(second.getByLabel(label, { exact: true })).toHaveValue('immediate');
        await second.close();
        const persisted = await api(reviewer, 'GET', '/settings/notifications');
        expect(persisted.preferences.find((p) => p.event_family === 'product').delivery).toBe(
          'immediate'
        );
        const isolated = await api(viewer, 'GET', '/settings/notifications');
        expect(isolated.version).toBe(0);
      });

      await test.step('cross-category shared-policy UI preserves drafts, confirms isolated writes and reconciles real admin conflict', async () => {
        const baseline = await policy(owner, false, 'public_allowed');
        const writes = [];
        const observe = (request) => {
          if (
            request.url().endsWith('/api/settings/workspace-policy') &&
            request.method() === 'PUT'
          ) {
            writes.push(request.postDataJSON());
          }
        };
        owner.page.on('request', observe);
        reviewer.page.on('request', observe);
        const policyForm = async (page, id) => {
          const control = page.locator(`#${id}`);
          // Exit animations may retain an outgoing card briefly. Never select a
          // hidden/detached duplicate or substitute first() for readiness.
          await expect(control).toHaveCount(1);
          await expect(control).toBeVisible();
          const form = page.locator('form').filter({ has: control });
          await expect(form).toHaveCount(1);
          return { control, form };
        };
        const category = async (page, name, id) => {
          const nav = page.getByRole('navigation', { name: 'Settings categories', exact: true });
          const link = nav.locator(`a[href="/settings/${name}"]`);
          await expect(link).toHaveCount(1);
          await link.click();
          return policyForm(page, id);
        };
        const confirm = async (page, form, expectedStatus = 200) => {
          await form.getByRole('button', { name: 'Save policy', exact: true }).click();
          const dialog = form.getByRole('alertdialog', {
            name: 'Confirm policy change',
            exact: true,
          });
          await expect(dialog).toBeVisible();
          const response = page.waitForResponse(
            (r) =>
              r.url().endsWith('/api/settings/workspace-policy') && r.request().method() === 'PUT'
          );
          await dialog.getByRole('button', { name: 'Confirm policy change', exact: true }).click();
          const saved = await response;
          expect(saved.status()).toBe(expectedStatus);
          return saved.json();
        };
        const persisted = async (expected) =>
          expect(await api(owner, 'GET', '/settings/workspace-policy')).toMatchObject(expected);
        try {
          await owner.page.goto(`${BASE}/settings/organization#workspace-publishing-review`);
          let review = await policyForm(owner.page, 'workspace-publishing-review');
          await expect(review.control).toHaveValue('optional');
          await review.control.selectOption('required');
          let visibility = await category(
            owner.page,
            'site-capabilities',
            'workspace-content-visibility'
          );
          await visibility.control.selectOption('members_only');
          await visibility.form.getByRole('button', { name: 'Save policy', exact: true }).click();
          const dialog = visibility.form.getByRole('alertdialog', {
            name: 'Confirm policy change',
            exact: true,
          });
          await expect(dialog).toContainText('Previously downloaded copies cannot be recalled.');
          await dialog.getByRole('button', { name: 'Keep editing', exact: true }).click();
          await expect(dialog).toHaveCount(0);
          await expect(visibility.control).toHaveValue('members_only');
          await persisted({
            version: baseline.version,
            require_review: false,
            public_access: 'public_allowed',
          });
          expect(writes).toHaveLength(0);
          const siteSaved = await confirm(owner.page, visibility.form);
          expect(writes).toEqual([
            {
              expected_version: baseline.version,
              require_review: false,
              public_access: 'members_only',
            },
          ]);
          expect(siteSaved.version).toBe(baseline.version + 1);
          await persisted({
            version: siteSaved.version,
            require_review: false,
            public_access: 'members_only',
          });
          review = await category(owner.page, 'organization', 'workspace-publishing-review');
          await expect(review.control).toHaveValue('required');
          await expect(review.form).toContainText('Effective saved value: Review not required');
          await review.form.getByRole('button', { name: 'Cancel', exact: true }).click();
          await expect(review.control).toHaveValue('optional');
          await persisted({
            version: siteSaved.version,
            require_review: false,
            public_access: 'members_only',
          });
          expect(writes).toHaveLength(1);

          // Reverse the dirty categories: Organization must not save Site's draft.
          visibility = await category(
            owner.page,
            'site-capabilities',
            'workspace-content-visibility'
          );
          await visibility.control.selectOption('public_allowed');
          review = await category(owner.page, 'organization', 'workspace-publishing-review');
          await review.control.selectOption('required');
          const organizationSaved = await confirm(owner.page, review.form);
          expect(writes[1]).toEqual({
            expected_version: siteSaved.version,
            require_review: true,
            public_access: 'members_only',
          });
          expect(organizationSaved.version).toBe(siteSaved.version + 1);
          await persisted({
            version: organizationSaved.version,
            require_review: true,
            public_access: 'members_only',
          });
          visibility = await category(
            owner.page,
            'site-capabilities',
            'workspace-content-visibility'
          );
          await expect(visibility.control).toHaveValue('public_allowed');
          await expect(visibility.form).toContainText(
            'Effective saved value: Active site members only'
          );
          await visibility.form.getByRole('button', { name: 'Cancel', exact: true }).click();
          await expect(visibility.control).toHaveValue('members_only');
          await persisted({
            version: organizationSaved.version,
            require_review: true,
            public_access: 'members_only',
          });
          expect(writes).toHaveLength(2);

          // Two actual administrators hold the same policy version. The newer
          // Site save must win; stale Organization confirmation cannot overwrite it.
          review = await category(owner.page, 'organization', 'workspace-publishing-review');
          await review.control.selectOption('optional');
          await reviewer.page.goto(
            `${BASE}/settings/site-capabilities#workspace-content-visibility`
          );
          const otherSite = await policyForm(reviewer.page, 'workspace-content-visibility');
          await expect(otherSite.control).toHaveValue('members_only');
          await otherSite.control.selectOption('public_allowed');
          const concurrent = await confirm(reviewer.page, otherSite.form);
          expect(concurrent.version).toBe(organizationSaved.version + 1);
          expect(writes[2]).toEqual({
            expected_version: organizationSaved.version,
            require_review: true,
            public_access: 'public_allowed',
          });
          await confirm(owner.page, review.form, 409);
          expect(writes[3]).toEqual({
            expected_version: organizationSaved.version,
            require_review: false,
            public_access: 'members_only',
          });
          await expect(review.control).toHaveValue('optional');
          await expect(review.control).toBeDisabled();
          await expect(
            review.form.getByRole('button', { name: 'Save policy', exact: true })
          ).toBeDisabled();
          const reloaded = owner.page.waitForResponse(
            (r) =>
              r.url().endsWith('/api/settings/workspace-policy') && r.request().method() === 'GET'
          );
          await review.form
            .getByRole('button', { name: 'Discard policy drafts and reload', exact: true })
            .click();
          expect((await reloaded).status()).toBe(200);
          await expect(review.control).toBeEnabled();
          await expect(review.control).toHaveValue('required');
          await owner.page.reload();
          review = await policyForm(owner.page, 'workspace-publishing-review');
          await expect(review.control).toHaveValue('required');
          await persisted({
            version: concurrent.version,
            require_review: true,
            public_access: 'public_allowed',
          });
          expect(writes).toHaveLength(4);
          await testInfo.attach('real-shared-policy-ui', {
            body: JSON.stringify({
              initialVersion: baseline.version,
              finalVersion: concurrent.version,
              writes,
            }),
            contentType: 'application/json',
          });
        } finally {
          owner.page.off('request', observe);
          reviewer.page.off('request', observe);
        }
      });
      expect(await api(owner, 'GET', '/settings/workspace-policy')).toMatchObject({
        require_review: true,
        public_access: 'public_allowed',
      });
      await preference(owner, 'disabled');
      const definition = await api(
        editor,
        'POST',
        '/content/v1/types',
        {
          typeKey: TYPE,
          name: 'Acceptance article',
          presetId: 'custom',
          fields: [
            { fieldKey: 'summary', label: 'Summary', fieldKind: 'short_text', indexed: true },
            { fieldKey: 'image', label: 'Image', fieldKind: 'image' },
          ],
        },
        201
      );
      await api(owner, 'POST', `/content/v1/types/${TYPE}/versions/${definition.version}/publish`, {
        expectedLockVersion: definition.lockVersion,
      });

      let published;
      await test.step('real beat consumes durable submission after content-worker restart; approval is independent', async () => {
        compose('stop', 'celery-content-worker');
        let draft = await record(editor, 'public-visibility');
        await transition(owner, draft, 'publish', 422);
        await transition(editor, draft, 'schedule', 422, {
          publishAt: new Date(Date.now() + 120_000).toISOString(),
          timezone: 'UTC',
        });
        await api(
          editor,
          'POST',
          `${RECORDS}/${draft.id}/assets/image`,
          {
            assetId: seeded.assetId,
            expectedVersion: draft.version,
            altText: 'Synthetic readiness fixture',
          },
          201
        );
        draft = await read(editor, draft);
        const submitted = await transition(editor, draft, 'submit_review');
        expect((await transition(owner, submitted, 'publish', 422)).detail).toBe(
          'content_review_required'
        );
        expect(
          (
            await transition(editor, submitted, 'schedule', 422, {
              publishAt: new Date(Date.now() + 120_000).toISOString(),
              timezone: 'UTC',
            })
          ).detail
        ).toBe('content_review_required');
        resumeService('celery-content-worker');
        await expect
          .poll(() => intentFor(snapshot(), submitted, reviewer)?.status, {
            timeout: 120_000,
            intervals: [1000, 2000, 5000],
          })
          .toBe('delivered');
        const proof = snapshot();
        const intent = intentFor(proof, submitted, reviewer);
        expect(proof.receipts.filter((r) => r.intentId === intent.id)).toHaveLength(1);
        await testInfo.attach('real-beat-after-worker-restart', {
          body: JSON.stringify(proof),
          contentType: 'application/json',
        });
        // Author is owner here, so rejection is self-review, not insufficient role.
        const ownDraft = await record(owner, 'self-approval');
        const ownSubmitted = await transition(owner, ownDraft, 'submit_review');
        expect((await approve(owner, ownSubmitted, 422)).detail).toBe(
          'content_review_independent_reviewer_required'
        );
        await approve(reviewer, submitted);
        published = await transition(owner, submitted, 'publish');
        expect(published.state).toBe('published');
      });

      await test.step('public direct/search disappear immediately while member reads/export/asset remain authorized', async () => {
        const publicRequest = await browser.newContext();
        try {
          const publicGet = (route) =>
            publicRequest.request.get(`${BASE}/api${route}`, { headers: { 'X-Tenant-Id': SITE } });
          expect((await publicGet(`/content/${TYPE}/${published.slug}`)).status()).toBe(200);
          await expect
            .poll(
              async () =>
                (await (await publicGet('/search?q=public-visibility')).json()).items.map(
                  (i) => i.id
                ),
              { timeout: 120_000, intervals: [1000, 2000, 5000] }
            )
            .toContain(published.id);
          const asset = await api(viewer, 'GET', `/content/v1/assets/${seeded.assetId}`);
          expect(asset.downloadGrant).toBeTruthy();
          await api(viewer, 'GET', `/content/v1/assets/${seeded.assetId}/content`, undefined, 200, {
            'Download-Grant': asset.downloadGrant,
          });
          const exported = await api(
            viewer,
            'POST',
            `/content/v1/types/${TYPE}/exports`,
            {
              format: 'json',
              schemaVersion: definition.version,
              fields: ['summary'],
            },
            201,
            { 'Idempotency-Key': 'workspace124-viewer-export' }
          );
          await expect
            .poll(
              async () =>
                (await api(viewer, 'GET', `/content/v1/types/${TYPE}/exports/${exported.id}`))
                  .status,
              { timeout: 120_000, intervals: [1000, 2000, 5000] }
            )
            .toBe('completed');
          const exportGrantStarted = performance.now();
          const grant = await api(
            viewer,
            'POST',
            `/content/v1/types/${TYPE}/exports/${exported.id}/download`
          );
          await policy(owner, true, 'members_only');
          const denied = await publicGet(`/content/${TYPE}/${published.slug}`);
          expect(denied.status()).toBe(404);
          expect(denied.headers()['cache-control']).toContain('no-store');
          expect(
            (await (await publicGet('/search?q=public-visibility')).json()).items.map((i) => i.id)
          ).not.toContain(published.id);
          expect((await read(viewer, published)).id).toBe(published.id);
          await api(
            viewer,
            'GET',
            `/content/v1/types/${TYPE}/exports/${exported.id}/content`,
            undefined,
            200,
            { 'Download-Grant': grant.grant }
          );
          const assetGrantStarted = performance.now();
          const freshAsset = await api(viewer, 'GET', `/content/v1/assets/${seeded.assetId}`);
          await api(viewer, 'GET', `/content/v1/assets/${seeded.assetId}/content`, undefined, 200, {
            'Download-Grant': freshAsset.downloadGrant,
          });
          // No supported suspension route exists. Only the fixed trusted setup
          // service may suspend this predetermined synthetic viewer. Runtime API
          // and worker containers never receive owner credentials.
          const revocation = JSON.parse(
            compose(
              'run',
              '--rm',
              '--no-deps',
              '-T',
              'workspace-fixture',
              'python',
              '/e2e-support/workspace_fixture.py',
              'suspend-viewer'
            )
          );
          expect(revocation.actorId).toBe(viewer.id);
          expect(revocation.status).toBe('suspended');
          await api(
            viewer,
            'GET',
            `/content/v1/types/${TYPE}/exports/${exported.id}/content`,
            undefined,
            404,
            { 'Download-Grant': grant.grant }
          );
          await api(viewer, 'GET', `/content/v1/assets/${seeded.assetId}/content`, undefined, 404, {
            'Download-Grant': freshAsset.downloadGrant,
          });
          // Both grants belonged to this actor and succeeded above. Enforce a
          // conservative one-second margin against the server's expiry, so denial
          // cannot pass just because a slow fixture action consumed the TTL.
          const exportElapsed = performance.now() - exportGrantStarted;
          const assetElapsed = performance.now() - assetGrantStarted;
          expect(grant.expiresIn).toBe(60);
          expect(freshAsset.expiresIn).toBe(60);
          expect(exportElapsed).toBeLessThan(grant.expiresIn * 1000 - 1000);
          expect(assetElapsed).toBeLessThan(freshAsset.expiresIn * 1000 - 1000);
          await testInfo.attach('own-unexpired-grants-after-fixture-suspension', {
            body: JSON.stringify({
              ...revocation,
              exportElapsedMs: exportElapsed,
              assetElapsedMs: assetElapsed,
              grantTtlSeconds: 60,
            }),
            contentType: 'application/json',
          });
          for (const deniedActor of [suspended, outsider]) {
            await api(deniedActor, 'GET', `${RECORDS}/${published.id}`, undefined, 404);
            await api(
              deniedActor,
              'GET',
              `/content/v1/types/${TYPE}/search?q=public`,
              undefined,
              404
            );
            await api(
              deniedActor,
              'GET',
              `/content/v1/types/${TYPE}/exports/${exported.id}/content`,
              undefined,
              404,
              { 'Download-Grant': grant.grant }
            );
            await api(
              deniedActor,
              'GET',
              `/content/v1/assets/${seeded.assetId}/content`,
              undefined,
              404,
              { 'Download-Grant': freshAsset.downloadGrant }
            );
          }
        } finally {
          await publicRequest.close();
        }
      });

      await test.step('semantic edits invalidate approval and revoked reviewer cannot authorize due publication', async () => {
        const draft = await record(editor, 'stale-approval');
        const submitted = await transition(editor, draft, 'submit_review');
        await approve(reviewer, submitted);
        const changed = await api(editor, 'PATCH', `${RECORDS}/${submitted.id}`, {
          expectedVersion: submitted.version,
          values: { summary: 'Changed semantic revision' },
        });
        expect((await approve(reviewer, submitted, 409)).detail).toBe('content_version_conflict');
        await transition(owner, changed, 'publish', 422);
        const next = await record(editor, 'revoked-scheduler');
        const pending = await transition(editor, next, 'submit_review');
        await approve(reviewer, pending);
        // Fence execution, not time: revocation must commit before any due job runs.
        compose('stop', 'celery-content-worker');
        const scheduled = await transition(editor, pending, 'schedule', 200, {
          publishAt: new Date(Date.now() + 5000).toISOString(),
          timezone: 'UTC',
        });
        await role(owner, reviewer, 'viewer');
        await approve(reviewer, pending, 404);
        resumeService('celery-content-worker');
        await expect
          .poll(
            () =>
              snapshot().scheduler.some(
                (a) => a.recordId === scheduled.id && a.action === 'content.publication_blocked'
              ),
            { timeout: 120_000, intervals: [1000, 2000, 5000] }
          )
          .toBe(true);
        expect((await read(owner, scheduled)).state).toBe('scheduled');
        await role(owner, reviewer, 'admin');
      });

      await test.step('local sink opt-out, UTC digest, process restart/replay and recipient revocation (controlled-clock service proof)', async () => {
        compose('stop', 'celery-beat', 'celery-content-worker');
        beatStopped = true;
        detachedControl = true;
        await preference(reviewer, 'disabled');
        const disabled = await transition(
          editor,
          await record(editor, 'disabled-notice'),
          'submit_review'
        );
        consume();
        expect(intentFor(snapshot(), disabled, reviewer).status).toBe('suppressed');
        await preference(reviewer, 'digest');
        const daily = await transition(
          editor,
          await record(editor, 'daily-notice'),
          'submit_review'
        );
        const assignmentClock = new Date(Date.now() + 1000);
        consume(assignmentClock.toISOString());
        const assigned = intentFor(snapshot(), daily, reviewer);
        const nextMidnight = Date.UTC(
          assignmentClock.getUTCFullYear(),
          assignmentClock.getUTCMonth(),
          assignmentClock.getUTCDate() + 1
        );
        expect(Date.parse(assigned.availableAt)).toBe(nextMidnight);
        expect(assigned.status).toBe('digest');
        expect(snapshot().receipts.some((r) => r.batchId === assigned.batchId)).toBe(false);
        consume(new Date(nextMidnight - 1).toISOString());
        expect(intentFor(snapshot(), daily, reviewer).status).toBe('digest');
        expect(snapshot().receipts.some((r) => r.batchId === assigned.batchId)).toBe(false);
        // Each detached control call is a new restricted worker container/process.
        consume(new Date(nextMidnight).toISOString());
        const delivered = snapshot();
        expect(intentFor(delivered, daily, reviewer).status).toBe('delivered');
        expect(delivered.receipts.filter((r) => r.batchId === assigned.batchId)).toHaveLength(1);
        // Each detached control call is a new restricted worker container/process.
        consume(new Date(nextMidnight).toISOString());
        expect(snapshot().receipts.filter((r) => r.batchId === assigned.batchId)).toHaveLength(1);
        await preference(reviewer, 'immediate');
        const revoked = await transition(
          editor,
          await record(editor, 'revoked-recipient'),
          'submit_review'
        );
        await role(owner, reviewer, 'viewer');
        consume();
        const final = snapshot();
        expect(intentFor(final, revoked, reviewer).status).toBe('suppressed');
        expect(
          final.receipts.some((r) => r.intentId === intentFor(final, revoked, reviewer).id)
        ).toBe(false);
        await testInfo.attach('controlled-clock-local-sink-not-beat', {
          body: JSON.stringify(final),
          contentType: 'application/json',
        });
      });
    } catch (error) {
      primaryFailure = error;
      throw error;
    } finally {
      detachedControl = false;
      const recoveryErrors = [];
      for (const service of [...(beatStopped ? ['celery-beat'] : []), 'celery-content-worker']) {
        try {
          resumeService(service);
        } catch (error) {
          recoveryErrors.push(String(error));
        }
      }
      for (const actor of Object.values(actors)) {
        try {
          await actor.context.close();
        } catch (error) {
          recoveryErrors.push(String(error));
        }
      }
      if (recoveryErrors.length) {
        await testInfo.attach('recovery-errors', {
          body: recoveryErrors.join('\n'),
          contentType: 'text/plain',
        });
        // Never replace the first assertion failure with a cleanup symptom.
        if (!primaryFailure)
          throw new Error('Workspace acceptance recovery failed; see attachment');
      }
    }
  });
});
