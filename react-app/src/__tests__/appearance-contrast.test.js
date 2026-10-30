import { readFileSync } from 'node:fs';

const appearanceCss = readFileSync(`${process.cwd()}/src/styles/appearance.css`, 'utf8');
const selector =
  "html[data-contrast='high'] .page-content:has(#settings-detail) :is(.text-violet-200, .text-violet-300)";
let style;

beforeEach(() => {
  style = document.createElement('style');
  style.textContent = appearanceCss;
  document.head.append(style);
  document.body.innerHTML = `
    <main class="app-shell-root">
      <div class="page-content">
        <header><p id="settings-kicker" class="text-violet-300">Account control center</p></header>
        <section id="settings-detail"><a id="settings-accent" class="text-violet-200" href="/admin">Organization controls</a></section>
      </div>
      <div class="page-content"><p id="other-accent" class="text-violet-300">Unrelated page accent</p></div>
    </main>`;
});

afterEach(() => {
  style.remove();
  document.body.innerHTML = '';
  delete document.documentElement.dataset.contrast;
  delete document.documentElement.dataset.colorMode;
});

test.each(['light', 'dark'])(
  'settings accents use the semantic high-contrast foreground in %s mode only',
  (mode) => {
    const rule = [...style.sheet.cssRules].find(
      (item) => item.selectorText?.replace(/\s+/g, ' ').trim() === selector
    );
    expect(
      rule,
      'a scoped semantic override must exist for hardcoded settings accent text'
    ).toBeDefined();
    expect(rule.style.getPropertyValue('color')).toBe('var(--color-text)');
    document.documentElement.dataset.colorMode = mode;
    document.documentElement.dataset.contrast = 'high';
    expect(document.getElementById('settings-kicker').matches(selector)).toBe(true);
    expect(document.getElementById('settings-accent').matches(selector)).toBe(true);
    expect(document.getElementById('other-accent').matches(selector)).toBe(false);
    document.documentElement.dataset.contrast = 'standard';
    expect(document.getElementById('settings-kicker').matches(selector)).toBe(false);
    expect(document.getElementById('settings-accent').matches(selector)).toBe(false);
  }
);
