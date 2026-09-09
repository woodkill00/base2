import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    const FrozenDate = class extends Date {
      constructor(...args: ConstructorParameters<typeof Date>) {
        super(...(args.length ? args : ['2026-09-09T12:00:00Z']));
      }

      static now() {
        return new Date('2026-09-09T12:00:00Z').valueOf();
      }
    };
    window.Date = FrozenDate as DateConstructor;
  });
  await page.route('**/*', async (route) => {
    const target = new URL(route.request().url());
    if (target.hostname === '127.0.0.1') {
      await route.continue();
      return;
    }
    await route.abort('blockedbyclient');
  });
});

const cases = {
  'german-reflow': {
    locale: 'de',
    direction: 'ltr',
    openMenu: 'Base2-Befehlsmenü öffnen',
    openUtility: 'Base2-Schnellzugriffe öffnen',
    utilityList: 'Base2-Schnellzugriffe',
    search: 'Base2-Schnellzugriff: Suche',
  },
  'arabic-rtl-touch': {
    locale: 'ar',
    direction: 'rtl',
    openMenu: 'فتح قائمة أوامر Base2',
    openUtility: 'فتح قائمة اختصارات Base2',
    utilityList: 'اختصارات Base2',
    search: 'اختصار Base2: بحث',
  },
} as const;

test('localized Obsidian navigation is actionable and reflows deterministically', async ({
  page,
}, testInfo) => {
  const scenario = cases[testInfo.project.name as keyof typeof cases];
  if (!scenario) {
    test.skip(true, 'Dedicated German and Arabic visual projects own this evidence');
    return;
  }

  await page.goto(`/${scenario.locale}`);
  await page.evaluate(() => document.fonts.ready);
  await expect(page.locator('html')).toHaveAttribute('lang', scenario.locale);
  await expect(page.locator('html')).toHaveAttribute('dir', scenario.direction);
  const navigation = page.getByTestId('base2-obsidian-navigation');
  await expect(navigation).toHaveAttribute('dir', scenario.direction);

  await page.getByRole('button', { name: scenario.openMenu }).click();
  await expect(page.getByTestId('base2-left-section-list')).toBeVisible();
  await page.keyboard.press('Escape');

  await page.getByRole('button', { name: scenario.openUtility }).click();
  const utilities = page.getByRole('listbox', { name: scenario.utilityList });
  await expect(utilities).toBeVisible();
  const disabled = utilities.getByRole('option', { name: /غير متاح|nicht verfügbar/ }).first();
  await expect(disabled).toBeDisabled();
  await expect(utilities).toHaveScreenshot(`obsidian-utilities-${scenario.locale}.png`, {
    animations: 'disabled',
  });

  await utilities.getByRole('option', { name: scenario.search, exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/${scenario.locale}/search$`));
});
