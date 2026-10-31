const { test, expect } = require('@playwright/test');
const { execFileSync } = require('node:child_process');
const path = require('node:path');
const { readCompleteSearchPage } = require('../support/search-contract');

// Deployment selection is closed in the runner/config/fixture, never browser input.
const SITE = 'journey-reference';
const BASE = process.env.E2E_BASE_URL || 'http://127.0.0.1:18080';
const PASSWORD = 'SyntheticE2e124!Password';
const ROOT = path.resolve(__dirname, '../..');
const FAMILIES = [
  { type: 'blog-post', prefix: '/blog' },
  { type: 'doc-page', prefix: '/docs' },
  { type: 'portfolio-item', prefix: '/portfolio' },
];
const QUERY = 'f124representative';

async function login(browser, identity, contexts) {
  const context = await browser.newContext();
  contexts.push(context); // Own cleanup even when login fails before returning an actor.
  const page = await context.newPage();
  await page.goto(`${BASE}/login`);
  await page.getByLabel('Email', { exact: true }).fill(identity.email);
  await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
  let response;
  for (let attempt = 0; attempt < 2; attempt += 1) {
    const pending = page.waitForResponse(
      (r) => r.url().endsWith('/api/auth/login') && r.request().method() === 'POST'
    );
    await page.getByRole('button', { name: 'Sign in', exact: true }).click();
    response = await pending;
    if (response.status() !== 429) break;
    const delay = Number(response.headers()['retry-after']);
    expect(Number.isFinite(delay) && delay > 0 && delay <= 61).toBe(true);
    if (attempt === 0) await new Promise((resolve) => setTimeout(resolve, (delay + 1) * 1000));
  }
  expect(response.status()).toBe(200);
  const { access_token: token } = await response.json();
  expect(token).toBeTruthy();
  await expect(page).toHaveURL(/\/dashboard$/);
  expect(
    (await context.cookies()).find((cookie) => cookie.name.endsWith('_refresh'))?.httpOnly
  ).toBe(true);
  return { context, page, token, ...identity };
}
async function api(actor, method, route, data, status = 200) {
  const csrf = (await actor.context.cookies()).find((cookie) =>
    cookie.name.endsWith('_csrf')
  )?.value;
  const response = await actor.context.request.fetch(`${BASE}/api${route}`, {
    method,
    data,
    headers: {
      Authorization: `Bearer ${actor.token}`,
      'X-Tenant-Id': SITE,
      ...(csrf ? { 'X-CSRF-Token': csrf } : {}),
    },
  });
  expect(response.status(), `${method} ${route}: ${await response.text()}`).toBe(status);
  return response.json();
}
async function savePolicy(page, category, id, value) {
  await page.goto(`${BASE}/settings/${category}#${id}`);
  const control = page.locator(`#${id}`);
  await expect(control).toHaveCount(1);
  await expect(control).toBeVisible();
  const form = page.locator('form').filter({ has: control });
  await expect(form).toHaveCount(1);
  await control.selectOption(value);
  await form.getByRole('button', { name: 'Save policy', exact: true }).click();
  const dialog = form.getByRole('alertdialog', { name: 'Confirm policy change', exact: true });
  await expect(dialog).toBeVisible();
  const pending = page.waitForResponse(
    (r) => r.url().endsWith('/api/settings/workspace-policy') && r.request().method() === 'PUT'
  );
  await dialog.getByRole('button', { name: 'Confirm policy change', exact: true }).click();
  const response = await pending;
  expect(response.status()).toBe(200);
  return response.json();
}

async function capturePublicAuthoring(page, testInfo, stage, publicContent, scope, saveLabel) {
  const originalViewport = page.viewportSize();
  expect(originalViewport).not.toBeNull();
  try {
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 900 });
      await expect(scope.getByLabel('Public excerpt', { exact: true })).toHaveValue(
        publicContent.excerpt
      );
      await expect(scope.getByLabel('Public body', { exact: true })).toHaveValue(
        publicContent.body
      );
      await expect
        .poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth))
        .toBe(true);
      for (const label of ['Public excerpt', 'Public body']) {
        const field = scope.getByLabel(label, { exact: true });
        await field.scrollIntoViewIfNeeded();
        await expect(field).toBeInViewport();
        await expect(field).toBeEditable();
      }
      const save = scope.getByRole('button', { name: saveLabel, exact: true });
      await save.scrollIntoViewIfNeeded();
      await expect(save).toBeInViewport();
      await expect(save).toBeEnabled();
      await save.click({ trial: true }); // Check reachability without submitting the filled draft.
      await testInfo.attach(`representative-public-authoring-${stage}-${width}`, {
        body: await page.screenshot({ fullPage: true }),
        contentType: 'image/png',
      });
    }
  } finally {
    await page.setViewportSize(originalViewport);
  }
}

async function initializePolicyThroughUI(owner, evidence) {
  const initial = await api(owner, 'GET', '/settings/workspace-policy');
  // Fresh post-migration fixture has no policy row: retain conservative defaults.
  expect(initial).toMatchObject({ require_review: true, public_access: 'members_only' });
  evidence.policies.push(initial);
  // No definitions or records exist during the temporary optional-review state.
  for (const change of [
    {
      category: 'organization',
      id: 'workspace-publishing-review',
      value: 'optional',
      review: false,
      visibility: 'members_only',
    },
    {
      category: 'organization',
      id: 'workspace-publishing-review',
      value: 'required',
      review: true,
      visibility: 'members_only',
    },
    {
      category: 'site-capabilities',
      id: 'workspace-content-visibility',
      value: 'public_allowed',
      review: true,
      visibility: 'public_allowed',
    },
  ]) {
    const saved = await savePolicy(owner.page, change.category, change.id, change.value);
    expect(saved).toMatchObject({
      require_review: change.review,
      public_access: change.visibility,
      version: evidence.policies.at(-1).version + 1,
    });
    expect(await api(owner, 'GET', '/settings/workspace-policy')).toMatchObject(saved);
    evidence.policies.push(saved);
  }
}

test.describe('Representative generated profile: real supported public families', () => {
  test.describe.configure({ mode: 'serial', retries: 0 });
  test('settings, independent review, search navigation and immediate visibility revocation', async ({
    browser,
  }, testInfo) => {
    test.setTimeout(600_000);
    expect(process.env.E2E_SITE_PROFILE).toBe(SITE);
    const seeded = JSON.parse(
      execFileSync(
        'docker',
        [
          'compose',
          '-p',
          'base2-e2e-isolated',
          '-f',
          path.join(ROOT, 'e2e/docker-compose.e2e.yml'),
          'exec',
          '-T',
          'celery-content-worker',
          'python',
          '/e2e-support/workspace_fixture.py',
          'snapshot',
        ],
        { cwd: ROOT, encoding: 'utf8', timeout: 60_000 }
      )
    );
    expect(seeded.site).toBe(SITE);
    expect(seeded.databaseRole).toBe('base2_workspace_worker_e2e');
    const actors = [];
    const contexts = [];
    const anonymous = await browser.newContext();
    let publicPage;
    const evidence = { site: SITE, policies: [], families: [] };
    let primaryFailure;
    try {
      publicPage = await anonymous.newPage();
      for (const name of ['owner', 'editor', 'reviewer'])
        actors.push(await login(browser, seeded.actors[name], contexts));
      const [owner, editor, reviewer] = actors;
      await test.step('discover and save scoped shared policy through actual settings UI', async () => {
        const discovery = await api(owner, 'GET', '/settings/capabilities');
        for (const id of ['workspace-policy.require_review', 'workspace-policy.public_access']) {
          expect(discovery.controls.some((control) => control.id === id)).toBe(true);
        }
        for (const id of ['content-workspace', 'blog', 'documentation', 'portfolio']) {
          expect(discovery.modules.find((module) => module.id === id)?.enabled).toBe(true);
        }
        await initializePolicyThroughUI(owner, evidence);
        await testInfo.attach('representative-settings', {
          body: await owner.page.screenshot({ fullPage: true }),
          contentType: 'image/png',
        });
      });
      const records = [];
      for (const family of FAMILIES) {
        await test.step(`normal API independent review and publication: ${family.type}`, async () => {
          const definition = await api(
            editor,
            'POST',
            '/content/v1/types',
            {
              typeKey: family.type,
              name: `Representative ${family.type}`,
              presetId: 'custom',
              fields: [
                { fieldKey: 'summary', label: 'Summary', fieldKind: 'short_text', indexed: true },
              ],
            },
            201
          );
          await api(
            owner,
            'POST',
            `/content/v1/types/${family.type}/versions/${definition.version}/publish`,
            { expectedLockVersion: definition.lockVersion }
          );
          const route = `/content/v1/types/${family.type}/records`;
          const slug = `${QUERY}-${family.type}`;
          const title = `Representative ${QUERY} ${family.type}`;
          const privateSummary = `Private internal ${family.type} note never for publication`;
          const excerpt = `Public ${family.type} excerpt`;
          const body = `Verified integrated ${family.type} public body`;
          let publicContent = { excerpt, body };
          let draft;
          if (family.type === 'blog-post') {
            // First definition is the only choice: prove normal create and edit UI writes.
            await editor.page.goto(`${BASE}/workspace`);
            await editor.page.getByRole('button', { name: 'New record', exact: true }).click();
            await editor.page.getByLabel('Title', { exact: true }).fill(title);
            await editor.page.getByLabel('Slug', { exact: true }).fill(slug);
            await editor.page.getByLabel('Summary', { exact: true }).fill(privateSummary);
            await editor.page.getByLabel('Public excerpt', { exact: true }).fill(excerpt);
            await editor.page.getByLabel('Public body', { exact: true }).fill(body);
            await capturePublicAuthoring(
              editor.page,
              testInfo,
              'create',
              publicContent,
              editor.page,
              'Create draft'
            );
            const creating = editor.page.waitForResponse(
              (r) => r.url().endsWith(`/api${route}`) && r.request().method() === 'POST'
            );
            await editor.page.getByRole('button', { name: 'Create draft', exact: true }).click();
            const created = await creating;
            expect(created.status()).toBe(201);
            draft = await created.json();
            expect(draft.publicContent).toEqual(publicContent);
            const inspector = editor.page.locator('[aria-label="Record details"]');
            await inspector.getByRole('button', { name: 'Edit fields', exact: true }).click();
            publicContent = { excerpt, body: `${body} edited through the workspace UI` };
            await inspector.getByLabel('Public body', { exact: true }).fill(publicContent.body);
            await capturePublicAuthoring(
              editor.page,
              testInfo,
              'edit',
              publicContent,
              inspector,
              'Save changes'
            );
            const saving = editor.page.waitForResponse(
              (r) =>
                r.url().endsWith(`/api${route}/${draft.id}`) && r.request().method() === 'PATCH'
            );
            await inspector.getByRole('button', { name: 'Save changes', exact: true }).click();
            const saved = await saving;
            expect(saved.status()).toBe(200);
            const updated = await saved.json();
            expect(updated.version).toBe(draft.version + 1);
            draft = updated;
            await expect(
              inspector.getByRole('button', { name: 'Edit fields', exact: true })
            ).toBeVisible();
            await expect(inspector).toContainText(publicContent.body);
          } else {
            draft = await api(
              editor,
              'POST',
              route,
              {
                title,
                slug,
                values: { summary: privateSummary },
                publicContent: { excerpt, body },
              },
              201
            );
          }
          const persisted = await api(editor, 'GET', `${route}/${draft.id}`);
          expect(persisted.publicContent).toEqual(publicContent);
          expect(persisted.values).toEqual({ summary: privateSummary });
          expect(persisted.version).toBe(draft.version);
          const submitted = await api(
            editor,
            'POST',
            `${route}/${draft.id}/transitions/submit_review`,
            { expectedVersion: draft.version }
          );
          expect(
            (
              await api(
                owner,
                'POST',
                `${route}/${draft.id}/transitions/publish`,
                { expectedVersion: submitted.version },
                422
              )
            ).detail
          ).toBe('content_review_required');
          await api(reviewer, 'POST', `${route}/${draft.id}/review-approval`, {
            expectedVersion: submitted.version,
          });
          const published = await api(owner, 'POST', `${route}/${draft.id}/transitions/publish`, {
            expectedVersion: submitted.version,
          });
          expect(published.state).toBe('published');
          records.push({
            ...family,
            ...published,
            title,
            privateSummary,
            publicContent,
            route,
            urlPath: `${family.prefix}/${slug}`,
          });
        });
      }
      const publicGet = (route) =>
        anonymous.request.get(`${BASE}/api${route}`, { headers: { 'X-Tenant-Id': SITE } });
      const search = async () => {
        const response = await publicGet(`/search?q=${QUERY}`);
        expect(response.status()).toBe(200);
        return readCompleteSearchPage(await response.json());
      };
      let before;
      await test.step('published family pages and actual returned search links render title and content', async () => {
        await expect
          .poll(
            async () => {
              before = await search();
              return records.every((record) =>
                before.items.some(
                  (item) => item.urlPath === record.urlPath && item.title === record.title
                )
              );
            },
            { timeout: 120_000, intervals: [1000, 2000, 5000] }
          )
          .toBe(true);
        expect(before.items).toHaveLength(3);
        for (const record of records) {
          expect(before.items.find((item) => item.urlPath === record.urlPath)?.excerpt).toBe(
            record.publicContent.excerpt
          );
          const response = await publicGet(`/content/${record.type}/${record.slug}`);
          expect(response.status()).toBe(200);
          const detail = await response.json();
          expect(detail).toMatchObject({
            id: record.id,
            contentType: record.type,
            title: record.title,
            excerpt: record.publicContent.excerpt,
            body: record.publicContent.body,
          });
          expect(JSON.stringify(detail)).not.toContain(record.privateSummary);
          expect(JSON.stringify(before)).not.toContain(record.privateSummary);
          await publicPage.goto(`${BASE}/search`);
          await publicPage.getByLabel('Search this site', { exact: true }).fill(QUERY);
          await publicPage
            .getByRole('search')
            .getByRole('button', { name: 'Search', exact: true })
            .click();
          const link = publicPage.getByRole('link', { name: record.title, exact: true });
          await expect(link).toHaveAttribute('href', record.urlPath);
          await link.click();
          await expect(publicPage).toHaveURL(`${BASE}${record.urlPath}`);
          await expect(
            publicPage.getByRole('heading', { name: record.title, exact: true })
          ).toBeVisible();
          await expect(publicPage.locator('article')).toContainText(record.publicContent.body);
          await expect(publicPage.locator('body')).not.toContainText(record.privateSummary);
          await testInfo.attach(`representative-public-${record.type}`, {
            body: await publicPage.screenshot({ fullPage: true }),
            contentType: 'image/png',
          });
          evidence.families.push({
            type: record.type,
            recordId: record.id,
            title: record.title,
            urlPath: record.urlPath,
            publicStatus: response.status(),
            detail,
          });
        }
      });
      await test.step('UI restriction immediately denies anonymous search, direct reads and public pages but preserves member workspace reads', async () => {
        const saved = await savePolicy(
          owner.page,
          'site-capabilities',
          'workspace-content-visibility',
          'members_only'
        );
        expect(saved).toMatchObject({
          require_review: true,
          public_access: 'members_only',
          version: evidence.policies.at(-1).version + 1,
        });
        evidence.policies.push(saved);
        const after = await search(); // One immediate request: never poll away a leak.
        expect(after.items).toEqual([]);
        for (const record of records) {
          const response = await publicGet(`/content/${record.type}/${record.slug}`);
          expect(response.status()).toBe(404);
          expect(response.headers()['cache-control']).toContain('no-store');
          const member = await api(editor, 'GET', `${record.route}/${record.id}`);
          expect(member).toMatchObject({
            id: record.id,
            state: 'published',
            values: { summary: record.privateSummary },
            publicContent: record.publicContent,
          });
          const pending = publicPage.waitForResponse((r) =>
            r.url().includes(`/api/content/${record.type}/${record.slug}`)
          );
          await publicPage.goto(`${BASE}${record.urlPath}`);
          expect((await pending).status()).toBe(404);
          await expect(
            publicPage.getByText('This page has not been published yet.', { exact: true })
          ).toBeVisible();
          await expect(
            publicPage.getByRole('heading', { name: record.title, exact: true })
          ).toHaveCount(0);
          await expect(publicPage.locator('article')).toHaveCount(0);
          await testInfo.attach(`representative-restricted-${record.type}`, {
            body: await publicPage.screenshot({ fullPage: true }),
            contentType: 'image/png',
          });
        }
        await testInfo.attach('representative-policy-visibility', {
          body: JSON.stringify({ ...evidence, before, after }),
          contentType: 'application/json',
        });
      });
    } catch (error) {
      primaryFailure = error;
      throw error;
    } finally {
      const recoveryErrors = [];
      for (const context of [anonymous, ...contexts]) {
        try {
          await context.close();
        } catch (error) {
          recoveryErrors.push(String(error));
        }
      }
      await testInfo.attach('representative-progress', {
        body: JSON.stringify(evidence),
        contentType: 'application/json',
      });
      if (recoveryErrors.length) {
        await testInfo.attach('recovery-errors', {
          body: recoveryErrors.join('\n'),
          contentType: 'text/plain',
        });
        if (!primaryFailure) throw new Error(recoveryErrors.join('\n'));
      }
    }
  });
});
