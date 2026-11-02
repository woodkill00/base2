import { test, expect } from './fixtures';
import { fulfillSessionFixture, setSessionFixture } from '../session-fixture';
import profile from '../../src/config/generated/base2-obsidian.json';

// Native App/shell journeys with synthetic API. Not evidence of live persistence.
for (const locale of ['en', 'de', 'ar']) {
  test(`shared policy category drafts remain isolated (${locale}, high contrast)`, async ({
    page,
  }) => {
    setSessionFixture(page, { id: 'policy-owner', email: 'policy@example.test', locale });
    let policy = {
      schema_version: 1,
      version: 4,
      require_review: false,
      public_access: 'public_allowed',
      scope: { site_id: profile.siteId, organization_id: '11111111-1111-4111-8111-111111111111' },
      provenance: 'explicit',
      permissions: { read: true, write: true },
      restrictions: [],
    };
    const writes: Record<string, unknown>[] = [];
    await page.route('**/*', async (route) => {
      if (await fulfillSessionFixture(route)) return;
      const url = new URL(route.request().url());
      if (!['127.0.0.1', 'localhost'].includes(url.hostname)) return route.abort();
      if (!url.pathname.startsWith('/api/')) return route.continue();
      const path = url.pathname;
      if (path === '/api/settings/capabilities')
        return route.fulfill({
          json: {
            schema_version: 1,
            categories: ['overview', 'organization', 'site-capabilities'].map((id) => ({ id })),
            controls: [
              {
                id: 'workspace-policy.require_review',
                category: 'organization',
                anchor: 'workspace-publishing-review',
                scope: 'organization',
                label: 'Publishing review',
                description: 'Review policy',
                synonyms: 'approval',
              },
              {
                id: 'workspace-policy.public_access',
                category: 'site-capabilities',
                anchor: 'workspace-content-visibility',
                scope: 'site',
                label: 'Workspace content visibility',
                description: 'Content policy',
                synonyms: 'visibility',
              },
            ],
            modules: [],
            locales: ['en', 'de', 'ar'],
          },
        });
      if (path === '/api/settings/workspace-policy') {
        if (route.request().method() === 'PUT') {
          const body = route.request().postDataJSON();
          writes.push(body);
          expect(body.expected_version).toBe(policy.version);
          policy = {
            ...policy,
            require_review: body.require_review,
            public_access: body.public_access,
            version: policy.version + 1,
          };
        }
        return route.fulfill({ json: policy });
      }
      if (path === '/api/settings/preferences')
        return route.fulfill({
          json: {
            version: 1,
            theme: 'light',
            contrast: 'high',
            motion: 'reduced',
            density: 'comfortable',
            locale,
            timezone: 'UTC',
            week_start: 'system',
          },
        });
      if (path === '/api/settings/notifications')
        return route.fulfill({ json: { schema_version: 1, version: 0, preferences: [] } });
      return route.fulfill({ json: { events: [], operations: [] } });
    });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.emulateMedia({ forcedColors: 'active', reducedMotion: 'reduce' });
    await page.goto('/settings/organization#workspace-publishing-review');
    const review = page.locator('#workspace-publishing-review');
    await expect(review).toBeEnabled();
    await review.selectOption('required');
    await page.locator('#settings-detail').evaluate((node) => node.scrollIntoView());
    await page.locator('a[href="/settings/site-capabilities"]').first().click();
    const visibility = page.locator('#workspace-content-visibility');
    await expect(visibility).toBeEnabled();
    await visibility.selectOption('members_only');
    const form = page.locator('form').filter({ has: visibility });
    await form.locator('button[type="submit"]').click();
    await page.getByRole('alertdialog').getByRole('button').first().click();
    await expect.poll(() => writes.length).toBe(1);
    expect(writes[0]).toEqual({
      expected_version: 4,
      require_review: false,
      public_access: 'members_only',
    });
    await page.locator('a[href="/settings/organization"]').first().click();
    await expect(review).toHaveValue('required');
    const reviewForm = page.locator('form').filter({ has: review });
    await reviewForm.locator('button[type="button"]').first().click();
    await expect(review).toHaveValue('optional');
    expect(writes).toHaveLength(1);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true
    );
  });
}
