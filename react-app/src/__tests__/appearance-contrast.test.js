import { readFileSync } from 'node:fs';

const appearanceCss = readFileSync(`${process.cwd()}/src/styles/appearance.css`, 'utf8');
const selector =
  "html[data-contrast='high'] .page-content:has(#settings-detail) :is(.text-violet-200, .text-violet-300)";
let style;

beforeEach(() => {
  style = document.createElement('style');
  style.textContent = '.text-violet-300 { color: rgb(196, 180, 255); }\n' + appearanceCss;
  document.head.append(style);
  document.body.innerHTML = `
    <main class="app-shell-root">
      <div class="page-content">
        <header><p id="settings-kicker" class="settings-kicker text-violet-300">Account control center</p></header>
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
  document.documentElement.style.removeProperty('--color-text');
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

test('standard light kicker inherits the actual page text, not an opposite-theme root token', () => {
  document.documentElement.dataset.colorMode = 'light';
  document.documentElement.dataset.contrast = 'standard';
  document.documentElement.style.setProperty('--color-text', 'rgb(255, 255, 255)');
  document.querySelector('header').style.color = 'rgb(15, 23, 42)';
  const kicker = document.getElementById('settings-kicker');
  expect(getComputedStyle(kicker).color).toBe('rgb(15, 23, 42)');
  expect(getComputedStyle(document.getElementById('other-accent')).color).toBe(
    'rgb(196, 180, 255)'
  );
  document.documentElement.dataset.colorMode = 'dark';
  expect(getComputedStyle(kicker).color).toBe('rgb(196, 180, 255)');
});

test('only forced-colors exposes the native Canvas backdrop without overriding user colors', () => {
  const rules = [...style.sheet.cssRules];
  const forced = rules.find((rule) => rule.conditionText === '(forced-colors: active)');
  expect(forced, 'the body backdrop must be observable only in forced-colors mode').toBeDefined();
  expect(forced.cssRules).toHaveLength(3);
  const bodyRule = [...forced.cssRules].find((rule) => rule.selectorText === 'body');
  expect(bodyRule.selectorText).toBe('body');
  expect(bodyRule.style.length).toBe(1);
  expect(bodyRule.style.getPropertyValue('background-color').toLowerCase()).toBe('canvas');
  expect(bodyRule.style.getPropertyPriority('background-color')).toBe('');
  expect(rules.some((rule) => rule.selectorText === 'body')).toBe(false);
  expect(appearanceCss).not.toContain('forced-color-adjust:');
});

test.each([
  [
    "[data-theme='obsidian'] .app-shell-root .base2-button--primary:not(:disabled)",
    { color: 'ButtonText', background: 'ButtonFace', 'border-color': 'ButtonText' },
  ],
  [
    "[role='tab'][aria-selected='true']",
    { 'text-decoration-line': 'underline', 'text-decoration-color': 'currentColor' },
  ],
])('forced colors supplies scoped system presentation for %s only', (selector, properties) => {
  const rules = [...style.sheet.cssRules];
  const forced = rules.find((rule) => rule.conditionText === '(forced-colors: active)');
  const rule = [...forced.cssRules].find((item) => item.selectorText === selector);
  expect(rule).toBeDefined();
  for (const [property, value] of Object.entries(properties)) {
    expect(rule.style.getPropertyValue(property).toLowerCase()).toBe(value.toLowerCase());
    expect(rule.style.getPropertyPriority(property)).toBe('');
  }
  expect(rules.some((item) => item.selectorText === selector)).toBe(false);
});

test('forced colors exposes picker search and status boundaries without targeting checkboxes', () => {
  const mediaStyle = document.createElement('style');
  mediaStyle.textContent = readFileSync(`${process.cwd()}/src/styles/media-library.css`, 'utf8');
  document.head.append(mediaStyle);
  try {
    const selector = '.media-picker > label > input, .media-picker > label > select';
    const rules = [...mediaStyle.sheet.cssRules];
    const forced = rules.find((rule) => rule.conditionText === '(forced-colors: active)');
    const rule = [...forced.cssRules].find(
      (item) => item.selectorText?.replace(/\s+/g, ' ') === selector
    );
    expect(rule).toBeDefined();
    expect(rule.style.getPropertyValue('border')).toBe('1px solid buttontext');
    expect(rule.style.getPropertyValue('color')).toBe('buttontext');
    expect(rule.style.getPropertyValue('background')).toBe('buttonface');
    const picker = document.createElement('section');
    picker.className = 'media-picker';
    picker.innerHTML =
      '<label>Search<input></label><label>Status<select></select></label><ul><li><label><input type="checkbox"></label></li></ul>';
    expect(picker.querySelector('label > input').matches(selector)).toBe(true);
    expect(picker.querySelector('select').matches(selector)).toBe(true);
    expect(picker.querySelector('[type="checkbox"]').matches(selector)).toBe(false);
    expect(rules.some((item) => item.selectorText === selector)).toBe(false);
  } finally {
    mediaStyle.remove();
  }
});

test('forced system selectors exclude disabled primary buttons and unselected tabs', () => {
  const root = document.createElement('div');
  root.dataset.theme = 'obsidian';
  root.innerHTML =
    '<main class="app-shell-root"><button class="base2-button--primary" role="tab" aria-selected="true">Records</button></main>';
  const button = root.querySelector('button');
  const primary = "[data-theme='obsidian'] .app-shell-root .base2-button--primary:not(:disabled)";
  const selected = "[role='tab'][aria-selected='true']";
  expect(button.matches(primary)).toBe(true);
  expect(button.matches(selected)).toBe(true);
  button.disabled = true;
  button.setAttribute('aria-selected', 'false');
  expect(button.matches(primary)).toBe(false);
  expect(button.matches(selected)).toBe(false);
});
