import { expect, test } from '@playwright/test';
import { readFileSync } from 'node:fs';

const axeSource = readFileSync('node_modules/axe-core/axe.min.js', 'utf8');
const typeId = '00000000-0000-0000-0000-000000010400';
const fieldKinds = [
  'short_text',
  'long_text',
  'rich_text',
  'integer',
  'decimal',
  'boolean',
  'date',
  'datetime',
  'enum',
  'slug',
  'url',
  'email',
  'location',
  'reference',
  'references',
  'image',
  'file',
  'json_object',
];
const fields = fieldKinds.map((fieldKind, index) => ({
  fieldKey: index === 0 ? 'title' : index === 9 ? 'slug' : `field_${index}`,
  label: index === 1 ? 'وصف طويل للاختبار المرئي' : `${fieldKind.replaceAll('_', ' ')} field`,
  fieldKind,
  required: index < 2,
  nullable: false,
  validation: fieldKind === 'enum' ? { choices: ['planned', 'ready'] } : {},
  presentation: {},
  readPermission: 'content.read',
  writePermission: 'content.write',
}));
const states = ['draft', 'in_review', 'scheduled', 'published', 'archived', 'deleted'];
const jobStates = [
  'queued',
  'validating',
  'validated',
  'review_required',
  'committing',
  'completed',
  'failed',
  'cancelled',
  'expired',
];
const mediaOutcomes = ['quarantined', 'scanning', 'validated', 'rejected', 'deleted'];
const relationshipOutcomes = ['empty', 'attached', 'restricted-delete', 'cascade-delete'];
const errorOutcomes = [
  'authorization-denied',
  'conflict',
  'validation-failed',
  'network-failed',
  'polling-exhausted',
];
const records = states.map((state, index) => ({
  id: `00000000-0000-0000-0000-0000000104${String(index).padStart(2, '0')}`,
  title:
    index === 1
      ? 'سجل طويل يثبت اتجاه النص وإعادة التدفق عبر الشاشات الصغيرة'
      : `${state.replaceAll('_', ' ')} record`,
  slug: `${state.replaceAll('_', '-')}-record`,
  state,
  schemaVersion: 1,
  version: index + 1,
  values: { title: `${state} record`, field_1: 'Deterministic synthetic content. '.repeat(4) },
}));
const fixtureUser = {
  id: '00000000-0000-0000-0000-000000010499',
  email: 'workspace-fixture@example.test',
  display_name: 'Workspace Fixture',
  permissions: [
    'content-workspace.read',
    'content.create',
    'content.write',
    'content.publish',
    'content.import',
    'content.export',
    'audit.read',
  ],
};

test('synthetic workspace fixture vocabulary is complete and explicit', () => {
  expect(fieldKinds).toHaveLength(18);
  expect(states).toEqual(['draft', 'in_review', 'scheduled', 'published', 'archived', 'deleted']);
  expect(jobStates).toContain('review_required');
  expect(jobStates).toContain('failed');
  expect(mediaOutcomes).toEqual(['quarantined', 'scanning', 'validated', 'rejected', 'deleted']);
  expect(relationshipOutcomes).toContain('restricted-delete');
  expect(errorOutcomes).toContain('authorization-denied');
});

test.beforeEach(async ({ page }, testInfo) => {
  await page.addInitScript((user) => {
    localStorage.setItem('user', JSON.stringify(user));
    localStorage.setItem('token', 'non-secret-workspace-fixture');
  }, fixtureUser);
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url());
    if (!['127.0.0.1', 'localhost'].includes(url.hostname)) return route.abort('blockedbyclient');
    if (!url.pathname.startsWith('/api/')) return route.continue();
    const send = (body: unknown, status = 200) =>
      route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
    if (url.pathname === '/api/content/v1/capabilities')
      return send({ schemaVersion: 1, enabled: true });
    if (url.pathname === '/api/content/v1/types')
      return send({
        items: [
          {
            id: typeId,
            typeKey: 'article',
            version: 1,
            name: 'Universal articles',
            status: 'published',
          },
        ],
      });
    if (url.pathname === '/api/content/v1/types/article/versions/1')
      return send({
        id: typeId,
        typeKey: 'article',
        version: 1,
        name: 'Universal articles',
        status: 'published',
        lockVersion: 2,
        fields,
      });
    if (url.pathname === '/api/content/v1/types/article/records')
      return send({ items: records, nextCursor: null });
    if (url.pathname === '/api/content/v1/types/article/views')
      return send({
        items: [
          {
            id: 'view-104',
            title: 'Ready for review',
            visibility: 'private',
            schemaVersion: 1,
            lockVersion: 1,
          },
        ],
      });
    const record = records.find((item) => url.pathname.endsWith(`/records/${item.id}`));
    if (record) return send(record);
    if (url.pathname.includes('/versions')) return send({ items: [] });
    if (url.pathname.includes('/relationships')) return send({ items: [] });
    return send({});
  });
  if (testInfo.project.name === 'chromium-large-text') {
    await page.addStyleTag({ content: 'html { font-size: 200% !important; }' });
  }
  await page.addStyleTag({
    content:
      '*,*::before,*::after{animation-duration:0s!important;transition-duration:0s!important;scroll-behavior:auto!important}',
  });
});

async function assertUsable(page) {
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)
  ).toBeLessThanOrEqual(1);
  const tiny = await page.locator('a,button,input,select,textarea').evaluateAll((nodes) =>
    nodes
      .filter((node) => {
        const target =
          node instanceof HTMLInputElement && ['checkbox', 'radio'].includes(node.type)
            ? node.closest('label') || node
            : node;
        const box = target.getBoundingClientRect();
        return box.width > 0 && box.height > 0 && (box.width < 24 || box.height < 24);
      })
      .map((node) => ({
        tag: node.tagName,
        type: node.getAttribute('type'),
        label: node.getAttribute('aria-label') || (node.textContent || '').trim().slice(0, 60),
        width: node.getBoundingClientRect().width,
        height: node.getBoundingClientRect().height,
      }))
  );
  expect(tiny).toEqual([]);
}

test('workspace release corpus is accessible, responsive, and visually stable', async ({
  page,
}, testInfo) => {
  await page.goto('/workspace');
  await expect(page.getByRole('heading', { name: /records · universal articles/i })).toBeVisible();
  await assertUsable(page);
  await page.addScriptTag({ content: axeSource });
  expect(
    await page.evaluate(async () =>
      (await window.axe.run(document, { resultTypes: ['violations'] })).violations.map(
        (item) => item.id
      )
    )
  ).toEqual([]);
  await page.keyboard.press('Tab');
  await expect(page.locator(':focus')).toBeVisible();
  await expect(page).toHaveScreenshot(`workspace-records-${testInfo.project.name}.png`, {
    fullPage: true,
    animations: 'disabled',
    caret: 'hide',
    maxDiffPixelRatio: 0.01,
  });

  await page.getByRole('tab', { name: 'Schemas' }).click();
  await expect(page.getByRole('heading', { name: /schema · universal articles/i })).toBeVisible();
  await page.evaluate(() => scrollTo(0, 0));
  await assertUsable(page);
  await expect(page).toHaveScreenshot(`workspace-schema-${testInfo.project.name}.png`, {
    fullPage: true,
    animations: 'disabled',
    caret: 'hide',
    maxDiffPixelRatio: 0.01,
  });

  for (const tab of ['Imports', 'Exports']) {
    await page.getByRole('tab', { name: tab }).click();
    await expect(
      page.getByRole('heading', { name: new RegExp(`${tab} · Universal articles`, 'i') })
    ).toBeVisible();
    await page.evaluate(() => scrollTo(0, 0));
    await assertUsable(page);
    await expect(page).toHaveScreenshot(
      `workspace-${tab.toLowerCase()}-${testInfo.project.name}.png`,
      { fullPage: true, animations: 'disabled', caret: 'hide', maxDiffPixelRatio: 0.01 }
    );
  }
});

declare global {
  interface Window {
    axe: {
      run: (root: Document, options?: unknown) => Promise<{ violations: Array<{ id: string }> }>;
    };
  }
}
