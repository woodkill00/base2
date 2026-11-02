import {
  ownershipStep,
  ownedScreenshot,
  ownedWorkspaceBody,
  ownedWorkspaceHook,
} from '../workspace-capture-ownership';
import { assertWorkspaceCheckpointsComplete } from '../workspace-scroll-checkpoints';
import { captureScrollportExtent } from '../scroll-target';
import { scrollPageTo, pageScrollTop } from '../scroll-target';
import { assertForcedColorState, assertForcedSystemControl } from '../forced-color-state';
import { setSessionFixture, fulfillSessionFixture } from '../session-fixture';
import { expect, test, type Page, type TestInfo } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { writeFile } from 'node:fs/promises';
import profile from '../../src/config/generated/base2-obsidian.json';
import { createRecordFixture } from './record-fixture';
import { measureSavedInspector, savedLabelFits } from './saved-readability';

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
  values: { title: `${state} record`, field_1: 'Private synthetic editorial note. '.repeat(4) },
  publicContent: {
    excerpt: `Curated public ${state} excerpt.`,
    body: `Intentional public ${state} body.`,
  },
}));
const fixtureUser = {
  id: '00000000-0000-0000-0000-000000010499',
  email: 'workspace-fixture@example.test',
  display_name: 'Workspace Fixture',
  permissions: [
    'content-workspace.read',
    'content-workspace.write',
    'content.create',
    'content.write',
    'content.publish',
    'content.import',
    'content.export',
    'audit.read',
  ],
};
const recordFixtures = new WeakMap<
  import('@playwright/test').Page,
  ReturnType<typeof createRecordFixture>
>();
const selectedEvidenceComplete = new WeakSet<import('@playwright/test').Page>();

test('synthetic workspace fixture vocabulary is complete and explicit', () => {
  expect(fieldKinds).toHaveLength(18);
  expect(fixtureUser.permissions).toContain('content-workspace.write');
  for (const record of records) {
    expect(record.publicContent.excerpt).not.toBe(record.publicContent.body);
    expect(JSON.stringify(record.publicContent)).not.toContain(record.values.field_1);
  }
  expect(states).toEqual(['draft', 'in_review', 'scheduled', 'published', 'archived', 'deleted']);
  expect(jobStates).toContain('review_required');
  expect(jobStates).toContain('failed');
  expect(mediaOutcomes).toEqual(['quarantined', 'scanning', 'validated', 'rejected', 'deleted']);
  expect(relationshipOutcomes).toContain('restricted-delete');
  expect(errorOutcomes).toContain('authorization-denied');
});

test.beforeEach(async ({ page }, testInfo) => {
  return ownedWorkspaceBody(
    page,
    testInfo,
    async () => {
      const recordFixture = createRecordFixture(records);
      recordFixtures.set(page, recordFixture);
      // Exercise an explicit owner preference, not merely the OS hint: Obsidian defaults dark.
      if (testInfo.project.name === 'chromium-light') {
        await ownershipStep(() =>
          page
            .context()
            .addCookies([{ name: 'theme', value: 'light', domain: '127.0.0.1', path: '/' }])
        );
      }
      setSessionFixture(page, fixtureUser);
      await ownershipStep(() =>
        page.route('**/*', async (route) => {
          if (await fulfillSessionFixture(route, { appearanceDefaults: true })) return;
          const url = new URL(route.request().url());
          if (!['127.0.0.1', 'localhost'].includes(url.hostname))
            return route.abort('blockedbyclient');
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
            return send({ items: recordFixture.list(), nextCursor: null });
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
          const record = recordFixture
            .list()
            .find((item) => url.pathname === `/api/content/v1/types/article/records/${item.id}`);
          if (record) {
            if (route.request().method() === 'PATCH') {
              const result = recordFixture.patch(
                record.id,
                route.request().headers()['if-match'],
                route.request().postDataJSON()
              );
              return send(result.body, result.status);
            }
            if (route.request().method() !== 'GET')
              return send({ detail: 'Synthetic method not supported' }, 405);
            return send(record);
          }
          if (url.pathname.includes('/versions')) return send({ items: [] });
          if (url.pathname.includes('/relationships')) return send({ items: [] });
          return send({});
        })
      );
      if (testInfo.project.name === 'chromium-large-text') {
        await ownershipStep(() =>
          page.addStyleTag({ content: 'html { font-size: 200% !important; }' })
        );
      }
      await ownershipStep(() =>
        page.addStyleTag({
          content:
            '*,*::before,*::after{animation-duration:0s!important;transition-duration:0s!important;scroll-behavior:auto!important}',
        })
      );
    },
    true
  );
});

async function assertRecordDivider(page) {
  const divider = page
    .getByRole('list', { name: 'Records', exact: true })
    .locator('li:not(:last-child)')
    .first();
  await ownershipStep(() => expect(divider).toBeVisible());
  const paint = await ownershipStep(() =>
    divider.evaluate((element) => {
      const style = getComputedStyle(element);
      const canvas = document.createElement('canvas');
      canvas.width = canvas.height = 1;
      const context = canvas.getContext('2d');
      if (!context) throw new Error('Canvas color inspection unavailable');
      const rgba = (color: string) => {
        context.clearRect(0, 0, 1, 1);
        context.fillStyle = color;
        context.fillRect(0, 0, 1, 1);
        return Array.from(context.getImageData(0, 0, 1, 1).data);
      };
      const probe = document.createElement('span');
      probe.setAttribute('aria-hidden', 'true');
      probe.style.cssText =
        'position:fixed;visibility:hidden;color:CanvasText;background-color:Canvas';
      document.body.append(probe);
      try {
        const system = getComputedStyle(probe);
        return {
          width: style.borderBottomWidth,
          style: style.borderBottomStyle,
          color: rgba(style.borderBottomColor),
          forcedColors: matchMedia('(forced-colors: active)').matches,
          systemText: rgba(system.color),
          systemCanvas: rgba(system.backgroundColor),
        };
      } finally {
        probe.remove();
      }
    })
  );
  expect(paint.width).toBe('1px');
  expect(paint.style).toBe('solid');
  if (paint.forcedColors) {
    // Respect the browser's accessibility palette; never disable forced colors.
    expect(paint.color).toEqual(paint.systemText);
    expect(paint.color[3]).toBe(255);
    expect(paint.color.slice(0, 3)).not.toEqual(paint.systemCanvas.slice(0, 3));
  } else {
    for (const channel of paint.color.slice(0, 3)) expect(channel).toBeGreaterThanOrEqual(254);
    expect(paint.color[3]).toBeGreaterThanOrEqual(25);
    expect(paint.color[3]).toBeLessThanOrEqual(26);
  }
}

async function assertUsable(page) {
  const typeFit = await ownershipStep(() =>
    page
      .getByRole('combobox', { name: 'Content type', exact: true })
      .evaluate((node: HTMLSelectElement) => {
        const style = getComputedStyle(node);
        const context = document.createElement('canvas').getContext('2d')!;
        context.font = style.font;
        const box = node.getBoundingClientRect();
        const parent = node.parentElement!.getBoundingClientRect();
        return {
          text: context.measureText(node.selectedOptions[0].text).width,
          available:
            node.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight) - 24,
          enclosed: box.left >= parent.left && box.right <= parent.right,
        };
      })
  );
  expect(typeFit.enclosed).toBe(true);
  expect(
    typeFit.available,
    'Content type must expose the selected label in its native control'
  ).toBeGreaterThanOrEqual(typeFit.text);
  expect(
    await ownershipStep(() =>
      page.evaluate(() => document.documentElement.scrollWidth - innerWidth)
    )
  ).toBeLessThanOrEqual(1);
  const tiny = await ownershipStep(() =>
    page.locator('a,button,input,select,textarea').evaluateAll((nodes) =>
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
    )
  );
  expect(tiny).toEqual([]);
}

async function prepareStableFullPageCapture(page) {
  await ownershipStep(() => scrollPageTo(page, 0));
  await ownershipStep(() => expect.poll(() => pageScrollTop(page)).toBe(0));
  await ownershipStep(() =>
    page.addStyleTag({
      content: '.volcano-header-frame{position:static!important}',
    })
  );
}

async function runCorpus(
  page: Page,
  testInfo: TestInfo,
  pair: 'records-schema' | 'imports-exports'
) {
  const evidence = {
    fixture: 'synthetic-api',
    project: testInfo.project.name,
    sourceCommit: process.env.GITHUB_SHA || null,
  };
  const captures: Array<{
    view: string;
    file: string;
    reference: string;
    comparison: string;
    forcedColors: string;
  }> = [];
  // Only stale HC image references are batched; functional/state/axe assertions remain hard.
  // Preserve each mismatch while independently ready views still execute.
  const visualExpect = expect.configure({ soft: true });
  const compareAndRetain = async (view: string, reference: string) => {
    await ownershipStep(() => assertForcedColorState(page, testInfo));
    if (testInfo.project.name === 'chromium-high-contrast') {
      const selected = page.getByRole('tab', { selected: true });
      await ownershipStep(() => expect(selected).toHaveCount(1));
      const cue = await ownershipStep(() =>
        selected.evaluate((element) => {
          const style = getComputedStyle(element);
          return {
            line: style.textDecorationLine,
            color: style.textDecorationColor,
            text: style.color,
          };
        })
      );
      expect(cue.line).toContain('underline');
      expect(cue.color).toBe(cue.text);
    }
    const errorsBefore = testInfo.errors.length;
    await ownershipStep(() =>
      visualExpect(page).toHaveScreenshot(reference, {
        fullPage: true,
        animations: 'disabled',
        caret: 'hide',
        maxDiffPixelRatio: 0.01,
      })
    );
    await ownershipStep(() => assertForcedColorState(page, testInfo));
    const file = `workspace-${view}-post-assert.png`;
    await ownershipStep(() =>
      ownedScreenshot(page, testInfo, {
        path: testInfo.outputPath(file),
        fullPage: true,
        animations: 'disabled',
        caret: 'hide',
      })
    );
    await ownershipStep(() => captureScrollportExtent(page, testInfo, `workspace-${view}`, 0.01));
    const forcedColors = await ownershipStep(() => assertForcedColorState(page, testInfo));
    captures.push({
      view,
      file,
      reference,
      forcedColors,
      comparison: testInfo.errors.length === errorsBefore ? 'passed' : 'failed',
    });
  };
  await ownershipStep(() => page.goto('/workspace'));
  await ownershipStep(() =>
    expect(page.getByRole('heading', { name: /records · universal articles/i })).toBeVisible()
  );
  const newRecord = page.getByRole('button', { name: 'New record', exact: true });
  await ownershipStep(() => expect(newRecord).toBeVisible());
  await ownershipStep(() => expect(newRecord).toBeEnabled());
  await ownershipStep(() => assertUsable(page));
  await ownershipStep(() => assertForcedColorState(page, testInfo));
  await ownershipStep(() => assertRecordDivider(page));
  if (testInfo.project.name === 'chromium-high-contrast') {
    await ownershipStep(() => assertForcedSystemControl(newRecord));
  }
  // Axe does not check non-text SVG contrast: the original edge-tab icon must
  // inherit its contrasting foreground, rather than the unrelated header color.
  expect(
    await ownershipStep(() =>
      page
        .locator('.home-left-menu-toggle')
        .first()
        .evaluate(
          (button) =>
            getComputedStyle(button.querySelector('svg')).color === getComputedStyle(button).color
        )
    )
  ).toBe(true);
  await ownershipStep(() => page.addScriptTag({ content: axeSource }));
  const violations = await ownershipStep(() =>
    page.evaluate(async () =>
      (await window.axe.run(document, { resultTypes: ['violations'] })).violations.map((item) => ({
        id: item.id,
        nodes: item.nodes.map((node) => ({
          target: node.target,
          summary: node.failureSummary,
        })),
      }))
    )
  );
  await ownershipStep(() =>
    writeFile(
      testInfo.outputPath('workspace-accessibility.json'),
      JSON.stringify({ ...evidence, violations }, null, 2)
    )
  );
  await ownershipStep(() => assertForcedColorState(page, testInfo));
  expect(violations).toEqual([]);
  await ownershipStep(() => page.keyboard.press('Tab'));
  await ownershipStep(() => expect(page.locator(':focus')).toBeVisible());
  await ownershipStep(() =>
    expect(page.locator('.volcano-header-frame')).toHaveCSS('position', 'sticky')
  );
  await ownershipStep(() => prepareStableFullPageCapture(page));
  const recordContainment = await ownershipStep(() =>
    page.getByRole('region', { name: 'Record details', exact: true }).evaluate((node) => {
      const inspector = node.getBoundingClientRect();
      const enclosure = document.querySelector('#workspace-detail')!.getBoundingClientRect();
      return (
        inspector.left >= enclosure.left - 1 &&
        inspector.right <= enclosure.right + 1 &&
        node.scrollWidth <= node.clientWidth + 1
      );
    })
  );
  expect(recordContainment, 'Record details must remain enclosed').toBe(true);
  if (pair === 'records-schema')
    await ownershipStep(() =>
      compareAndRetain('records', `workspace-records-${testInfo.project.name}.png`)
    );

  await ownershipStep(() => page.getByRole('tab', { name: 'Schemas' }).click());
  await ownershipStep(() =>
    expect(page.getByRole('heading', { name: /schema · universal articles/i })).toBeVisible()
  );
  await ownershipStep(() => scrollPageTo(page, 0));
  await ownershipStep(() => assertUsable(page));
  if (pair === 'records-schema')
    await ownershipStep(() =>
      compareAndRetain('schema', `workspace-schema-${testInfo.project.name}.png`)
    );

  for (const tab of pair === 'imports-exports' ? ['Imports', 'Exports'] : []) {
    await ownershipStep(() => page.getByRole('tab', { name: tab }).click());
    await ownershipStep(() =>
      expect(
        page.getByRole('heading', { name: new RegExp(`${tab} · Universal articles`, 'i') })
      ).toBeVisible()
    );
    await ownershipStep(() => scrollPageTo(page, 0));
    await ownershipStep(() => assertUsable(page));
    if (tab === 'Imports') {
      const filename = 'synthetic-workspace-records-for-review.json';
      const input = page.getByLabel('Import file', { exact: true });
      await ownershipStep(() =>
        input.setInputFiles({
          name: filename,
          mimeType: 'application/json',
          buffer: Buffer.from('[]'),
        })
      );
      await ownershipStep(() =>
        expect(input).toHaveAccessibleDescription(`Selected file: ${filename}`)
      );
      const policy = page.getByRole('combobox', { name: 'Commit policy', exact: true });
      await ownershipStep(() => expect(policy).toHaveValue('all_or_nothing'));
      const fit = await ownershipStep(() =>
        policy.evaluate((node: HTMLSelectElement) => {
          const style = getComputedStyle(node);
          const canvas = document.createElement('canvas');
          const context = canvas.getContext('2d')!;
          context.font = style.font;
          const textWidth = context.measureText(node.selectedOptions[0].text).width;
          // Reserve native arrow space in addition to authored padding.
          return {
            available:
              node.clientWidth -
              parseFloat(style.paddingLeft) -
              parseFloat(style.paddingRight) -
              24,
            textWidth,
          };
        })
      );
      expect(
        fit.available,
        'Commit policy must expose its full selected meaning'
      ).toBeGreaterThanOrEqual(fit.textWidth);
      const status = page.getByText(`Selected file: ${filename}`, { exact: true });
      const contained = await ownershipStep(() =>
        status.evaluate((node) => {
          const box = node.getBoundingClientRect();
          const form = node.closest('form')!.getBoundingClientRect();
          const range = document.createRange();
          range.selectNodeContents(node);
          return (
            box.left >= form.left &&
            box.right <= form.right &&
            [...range.getClientRects()].every(
              (rect) => rect.left >= box.left - 1 && rect.right <= box.right + 1
            )
          );
        })
      );
      expect(contained, 'Selected filename must wrap within the import form').toBe(true);
    }
    await ownershipStep(() =>
      compareAndRetain(
        tab.toLowerCase(),
        `workspace-${tab.toLowerCase()}-${testInfo.project.name}.png`
      )
    );
  }
  const failed = testInfo.errors.length > 0;
  await ownershipStep(() =>
    writeFile(
      testInfo.outputPath('workspace-release-summary.json'),
      JSON.stringify(
        {
          ...evidence,
          scenario: pair,
          status: failed ? 'failed' : 'passed',
          phase: failed ? 'assertions-completed-with-failures' : 'assertions-completed',
          captures,
          comparisonThresholdUnchanged: 0.01,
        },
        null,
        2
      )
    )
  );
}

test('workspace records and schema are accessible, responsive, and visually stable', async ({
  page,
}, testInfo) => {
  return ownedWorkspaceBody(page, testInfo, () => runCorpus(page, testInfo, 'records-schema'));
});

test('workspace imports and exports are accessible, responsive, and visually stable', async ({
  page,
}, testInfo) => {
  return ownedWorkspaceBody(page, testInfo, () => runCorpus(page, testInfo, 'imports-exports'));
});

test('selected record editing stays contained and saves or discards explicitly', async ({
  page,
}, testInfo) => {
  test.skip(
    !['chromium-compact', 'chromium-large-text', 'chromium-desktop'].includes(
      testInfo.project.name
    ),
    'Selected edit-state coverage is explicitly scoped to compact, large text and desktop.'
  );
  return ownedWorkspaceBody(page, testInfo, async () => {
    await ownershipStep(() => page.goto('/workspace'));
    if (testInfo.project.name === 'chromium-large-text') {
      await ownershipStep(() =>
        page.addStyleTag({ content: 'html { font-size: 200% !important; }' })
      );
      await ownershipStep(() => expect(page.locator('html')).toHaveCSS('font-size', '32px'));
    }
    const fixture = recordFixtures.get(page)!;
    const original = fixture.read(records[0].id)!;
    await ownershipStep(() =>
      page.getByRole('button', { name: 'Open draft record', exact: true }).click()
    );
    const inspector = page.getByRole('region', { name: 'Record details', exact: true });
    await ownershipStep(() =>
      expect(inspector.getByRole('heading', { name: 'draft record', exact: true })).toBeVisible()
    );
    await ownershipStep(() =>
      inspector.getByRole('button', { name: 'Edit fields', exact: true }).click()
    );
    const form = inspector.getByRole('form', { name: 'Edit record', exact: true });
    const title = form.getByLabel('short text field', { exact: true });
    await ownershipStep(() => title.focus());
    await ownershipStep(() => expect(title).toBeFocused());
    await ownershipStep(() => page.keyboard.press('Tab'));
    await ownershipStep(() =>
      expect(
        form.getByRole('textbox', { name: 'وصف طويل للاختبار المرئي', exact: true })
      ).toBeFocused()
    );
    await ownershipStep(() => title.fill('Discarded synthetic title'));
    await ownershipStep(() =>
      form.getByRole('button', { name: 'Discard changes', exact: true }).click()
    );
    await ownershipStep(() => expect(form).toHaveCount(0));
    expect(fixture.updates).toBe(0);
    expect(fixture.read(original.id)).toEqual(original);
    await ownershipStep(() =>
      inspector.getByRole('button', { name: 'Edit fields', exact: true }).click()
    );
    await ownershipStep(() => expect(title).toHaveValue('draft record'));
    await ownershipStep(() => title.fill('Saved synthetic title'));
    await ownershipStep(() =>
      form.getByLabel('Public body', { exact: true }).fill('Explicitly edited public fixture body.')
    );
    await ownershipStep(() =>
      expect(form.getByRole('button', { name: 'Save changes', exact: true })).toBeEnabled()
    );
    // New diagnostic state, never an automatically approved reference.
    await ownershipStep(() =>
      ownedScreenshot(page, testInfo, {
        path: testInfo.outputPath('workspace-records-selected-edit-post-assert.png'),
        fullPage: true,
        animations: 'disabled',
        caret: 'hide',
      })
    );
    await ownershipStep(() =>
      captureScrollportExtent(page, testInfo, 'workspace-records-selected-edit')
    );
    const breaches = await ownershipStep(() =>
      form.evaluate((node) => {
        const card = document.querySelector('#workspace-detail')!.getBoundingClientRect();
        const panel = node.closest('[role="region"]')!;
        const bounds = panel.getBoundingClientRect();
        const targets = [
          panel,
          node,
          ...panel.querySelectorAll('section,fieldset,form,label,input,select,textarea,button'),
        ];
        return targets.flatMap((target, index) => {
          const box = target.getBoundingClientRect();
          if (!box.width || !box.height) return [];
          return box.left < card.left - 1 ||
            box.right > card.right + 1 ||
            box.left < bounds.left - 1 ||
            box.right > bounds.right + 1 ||
            target.scrollWidth > target.clientWidth + 1
            ? [
                {
                  index,
                  left: box.left,
                  right: box.right,
                  cardLeft: card.left,
                  cardRight: card.right,
                },
              ]
            : [];
        });
      })
    );
    expect(
      breaches,
      'Selected editing labels and actions must stay enclosed without clipping'
    ).toEqual([]);
    await ownershipStep(() => page.addScriptTag({ content: axeSource }));
    expect(
      await ownershipStep(() =>
        page.evaluate(async () =>
          (await window.axe.run(document)).violations.map((item) => item.id)
        )
      )
    ).toEqual([]);
    await ownershipStep(() =>
      form.getByRole('button', { name: 'Save changes', exact: true }).click()
    );
    await ownershipStep(() => expect(form).toHaveCount(0));
    await ownershipStep(() =>
      expect(
        inspector.getByRole('heading', { name: 'Saved synthetic title', exact: true })
      ).toBeVisible()
    );
    expect(fixture.updates).toBe(1);
    expect(fixture.read(original.id)).toMatchObject({
      version: original.version + 1,
      values: { ...original.values, title: 'Saved synthetic title' },
      publicContent: { ...original.publicContent, body: 'Explicitly edited public fixture body.' },
    });
    // Exercise an actual intercepted stale PATCH; never forward a write to a provider.
    const stale = await ownershipStep(() =>
      page.evaluate(async ({ id, version, values, publicContent }) => {
        const response = await fetch(`/api/content/v1/types/article/records/${id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json', 'If-Match': `"${version}"` },
          body: JSON.stringify({ values, publicContent }),
        });
        return response.status;
      }, original)
    );
    expect(stale).toBe(409);
    expect(fixture.updates).toBe(1);
    await ownershipStep(() => page.reload());
    if (testInfo.project.name === 'chromium-large-text') {
      await ownershipStep(() =>
        page.addStyleTag({ content: 'html { font-size: 200% !important; }' })
      );
    }
    await ownershipStep(() =>
      page.getByRole('button', { name: 'Open Saved synthetic title', exact: true }).click()
    );
    await ownershipStep(() =>
      expect(
        inspector.getByText('Explicitly edited public fixture body.', { exact: true })
      ).toBeVisible()
    );
    await ownershipStep(() =>
      ownedScreenshot(page, testInfo, {
        path: testInfo.outputPath('workspace-records-selected-saved-post-assert.png'),
        fullPage: true,
        animations: 'disabled',
        caret: 'hide',
      })
    );
    await ownershipStep(() =>
      captureScrollportExtent(page, testInfo, 'workspace-records-selected-saved')
    );
    // Retain the exact saved/reloaded pixels before any readability failure.
    const savedLayout = await ownershipStep(() => inspector.evaluate(measureSavedInspector));
    expect(savedLayout.breaches, 'Saved controls must remain enclosed').toEqual([]);
    expect(savedLayout.counts).toEqual({
      'Secure file': 2,
      'Add relationship': 1,
      'Submit for review': 1,
      Publish: 1,
      'Delete record': 1,
      relationship: 1,
      files: 2,
    });
    for (const label of savedLayout.labels)
      expect(
        savedLabelFits(label),
        `Saved ${label.label} must expose its full label: ${JSON.stringify(label)}`
      ).toBe(true);
    selectedEvidenceComplete.add(page);
  });
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

test.afterEach(async ({ page }, testInfo) => {
  // The new selected-state case retains both named edit and saved states itself.
  // On an early failure the ordinary fallback still attempts evidence.
  await ownedWorkspaceHook(
    page,
    testInfo,
    async () => {
      await captureScrollportExtent(page, testInfo);
      assertWorkspaceCheckpointsComplete(testInfo);
    },
    selectedEvidenceComplete.has(page)
  );
});
