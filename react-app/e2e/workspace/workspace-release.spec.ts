import { setSessionFixture, fulfillSessionFixture } from '../session-fixture';
import { expect, test } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { writeFile } from 'node:fs/promises';
import profile from '../../src/config/generated/base2-obsidian.json';

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
const fixtureActions: Record<string, string[]> = {
  draft: ['submit_review', 'publish', 'delete'],
  in_review: ['return_draft', 'publish', 'delete'],
  scheduled: ['return_draft', 'publish', 'archive'],
  published: ['archive'],
  archived: ['restore', 'delete'],
  deleted: [],
};
const records = states.map((state, index) => ({
  siteId: profile.siteId,
  typeKey: 'article',
  updatedAt: '2026-10-31T00:00:00Z',
  allowedActions: fixtureActions[state],
  review: {
    status: state === 'in_review' ? 'pending' : 'not_requested',
    requiresReview: false,
    policyVersion: 1,
    semanticRevision: 'fixture-revision',
    deliveryAdapter: 'local_test',
    recoveryReason: null,
  },

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
  // Exercise an explicit owner preference, not merely the OS hint: Obsidian defaults dark.
  if (testInfo.project.name === 'chromium-light') {
    await page
      .context()
      .addCookies([{ name: 'theme', value: 'light', domain: '127.0.0.1', path: '/' }]);
  }
  setSessionFixture(page, fixtureUser);
  await page.route('**/*', async (route) => {
    if (await fulfillSessionFixture(route, { appearanceDefaults: true })) return;
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

async function prepareStableFullPageCapture(page) {
  await page.evaluate(() => scrollTo(0, 0));
  await expect.poll(() => page.evaluate(() => scrollY)).toBe(0);
  await page.addStyleTag({
    content: '.volcano-header-frame{position:static!important}',
  });
}

test('workspace release corpus is accessible, responsive, and visually stable', async ({
  page,
}, testInfo) => {
  const evidence = {
    fixture: 'synthetic-api',
    project: testInfo.project.name,
    sourceCommit: process.env.GITHUB_SHA || null,
  };
  const captures: Array<{ view: string; file: string; reference: string }> = [];
  const retainCapture = async (view: string, reference: string) => {
    const file = `workspace-${view}-post-assert.png`;
    await page.screenshot({
      path: testInfo.outputPath(file),
      fullPage: true,
      animations: 'disabled',
      caret: 'hide',
    });
    captures.push({ view, file, reference });
  };
  await page.goto('/workspace');
  await expect(page.getByRole('heading', { name: /records · universal articles/i })).toBeVisible();
  await assertUsable(page);
  // Axe does not check non-text SVG contrast: the original edge-tab icon must
  // inherit its contrasting foreground, rather than the unrelated header color.
  expect(
    await page
      .locator('.home-left-menu-toggle')
      .first()
      .evaluate(
        (button) =>
          getComputedStyle(button.querySelector('svg')).color === getComputedStyle(button).color
      )
  ).toBe(true);
  await page.addScriptTag({ content: axeSource });
  const violations = await page.evaluate(async () =>
    (await window.axe.run(document, { resultTypes: ['violations'] })).violations.map((item) => ({
      id: item.id,
      nodes: item.nodes.map((node) => ({ target: node.target, summary: node.failureSummary })),
    }))
  );
  await writeFile(
    testInfo.outputPath('workspace-accessibility.json'),
    JSON.stringify({ ...evidence, violations }, null, 2)
  );
  expect(violations).toEqual([]);
  await page.keyboard.press('Tab');
  await expect(page.locator(':focus')).toBeVisible();
  await expect(page.locator('.volcano-header-frame')).toHaveCSS('position', 'sticky');
  await prepareStableFullPageCapture(page);
  await expect(page).toHaveScreenshot(`workspace-records-${testInfo.project.name}.png`, {
    fullPage: true,
    animations: 'disabled',
    caret: 'hide',
    maxDiffPixelRatio: 0.01,
  });
  await retainCapture('records', `workspace-records-${testInfo.project.name}.png`);

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
  await retainCapture('schema', `workspace-schema-${testInfo.project.name}.png`);

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
    await retainCapture(
      tab.toLowerCase(),
      `workspace-${tab.toLowerCase()}-${testInfo.project.name}.png`
    );
  }
  await writeFile(
    testInfo.outputPath('workspace-release-summary.json'),
    JSON.stringify(
      { ...evidence, phase: 'assertions-completed', captures, comparisonThresholdUnchanged: 0.01 },
      null,
      2
    )
  );
});

declare global {
  interface Window {
    axe: {
      run: (
        root: Document,
        options?: unknown
      ) => Promise<{
        violations: Array<{
          id: string;
          nodes: Array<{ target: unknown; failureSummary?: string }>;
        }>;
      }>;
    };
  }
}
