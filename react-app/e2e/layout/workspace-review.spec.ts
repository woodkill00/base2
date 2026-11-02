import { test, expect } from './fixtures';
import { fulfillSessionFixture, setSessionFixture } from '../session-fixture';
import profile from '../../src/config/generated/base2-obsidian.json';

for (const action of ['approve_review', 'adopt_review_subject', 'review_recovery']) {
  test(`server-authoritative ${action} has explicit safe review controls`, async ({ page }) => {
    setSessionFixture(page, {
      id: 'review-owner',
      email: 'review@example.test',
      permissions: ['content-workspace.read', 'content-workspace.write'],
    });
    let record = {
      id: 'record-1',
      siteId: profile.siteId,
      typeKey: 'article',
      schemaVersion: 1,
      updatedAt: '2026-10-31T00:00:00Z',
      title: 'Review fixture',
      slug: 'review-fixture',
      state: action === 'adopt_review_subject' ? 'published' : 'in_review',
      version: 2,
      values: { title: 'Review fixture' },
      publicContent: { excerpt: 'Public review excerpt', body: 'Public review body' },
      allowedActions: action === 'review_recovery' ? ['return_draft'] : [action],
      review: {
        status: action === 'adopt_review_subject' ? 'authorship_unknown' : 'pending',
        requiresReview: true,
        policyVersion: 4,
        semanticRevision: 'revision-fixture',
        deliveryAdapter: 'local_test',
        recoveryReason: action === 'review_recovery' ? 'no_independent_reviewer' : null,
      },
    };
    let writes = 0;
    await page.route('**/*', async (route) => {
      if (await fulfillSessionFixture(route)) return;
      const url = new URL(route.request().url());
      if (!['127.0.0.1', 'localhost'].includes(url.hostname)) return route.abort();
      if (!url.pathname.startsWith('/api/')) return route.continue();
      const path = url.pathname;
      if (path === '/api/content/v1/types')
        return route.fulfill({
          json: { items: [{ typeKey: 'article', version: 1, name: 'Articles' }] },
        });
      if (path === '/api/content/v1/types/article/versions/1')
        return route.fulfill({
          json: {
            typeKey: 'article',
            version: 1,
            name: 'Articles',
            fields: [{ fieldKey: 'title', label: 'Title', fieldKind: 'short_text' }],
          },
        });
      if (path === '/api/content/v1/types/article/records')
        return route.fulfill({ json: { items: [record] } });
      if (path.endsWith('/review-approval') || path.endsWith('/review-subject')) {
        writes += 1;
        expect(route.request().postDataJSON()).toEqual(
          action === 'approve_review'
            ? { expected_version: 2 }
            : { expected_version: 2, adopt_snapshot: true }
        );
        record = {
          ...record,
          version: 3,
          state: action === 'approve_review' ? 'in_review' : 'draft',
          allowedActions: [],
          review: {
            ...record.review,
            status: action === 'approve_review' ? 'approved' : 'not_requested',
          },
        };
        return route.fulfill({
          json: {
            record_id: record.id,
            version: 3,
            state: record.state,
            review_status: action === 'approve_review' ? 'approved' : 'draft',
          },
        });
      }
      if (path === '/api/content/v1/types/article/records/record-1')
        return route.fulfill({ json: record });
      return route.fulfill({ json: { items: [] } });
    });
    await page.goto('/workspace#records');
    await page.getByRole('button', { name: /Review fixture/ }).click();
    await expect(page.getByRole('button', { name: 'Publish', exact: true })).toHaveCount(0);
    await expect(page.getByText(/durable test receipts, not live email/)).toBeVisible();
    if (action === 'review_recovery') {
      await expect(
        page.getByRole('link', { name: 'Open organization administration' })
      ).toHaveAttribute('href', '/admin');
      await expect(page.getByText(/This request remains pending/)).toBeVisible();
      await expect(page.getByRole('button', { name: 'Approve review', exact: true })).toHaveCount(
        0
      );
      expect(writes).toBe(0);
      return;
    }
    await page
      .getByRole('button', {
        name: action === 'approve_review' ? 'Approve review' : 'Adopt current snapshot',
        exact: true,
      })
      .click();
    expect(writes).toBe(0);
    if (action === 'adopt_review_subject')
      await expect(page.getByRole('alertdialog')).toContainText('never publishes');
    await page.getByRole('button', { name: 'Confirm action', exact: true }).click();
    await expect(
      page
        .getByRole('region', { name: 'Record details' })
        .getByText(`${record.state} · version 3`, { exact: true })
    ).toBeVisible();
    expect(writes).toBe(1);
    await expect(page.getByRole('button', { name: 'Publish', exact: true })).toHaveCount(0);
  });
}
