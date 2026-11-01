// Exact allowlisted synthetic diagnostics: no text, values, HTML, URLs or network data.
export function safeFocusSnapshot(raw: Record<string, unknown>) {
  const allowed = (value: unknown, values: string[]) =>
    typeof value === 'string' && values.includes(value) ? value : 'unlisted';
  return {
    schemaVersion: 1,
    fixtureScope: 'synthetic-project-tests',
    tag: allowed(raw.tag, ['A', 'BUTTON', 'INPUT', 'TEXTAREA', 'SELECT', 'MAIN', 'DIV', 'BODY']),
    id: allowed(raw.id, [
      '',
      'main-content',
      'name',
      'email',
      'message',
      'contact-name',
      'contact-email',
      'contact-message',
    ]),
    role: allowed(raw.role, [
      '',
      'button',
      'dialog',
      'alertdialog',
      'menuitem',
      'navigation',
      'main',
    ]),
    testId: allowed(raw.testId, [
      '',
      'volcano-scrollport',
      'base2-left-menu-toggle',
      'base2-right-utility-toggle',
      'base2-scroll-ascend',
      'base2-scroll-descend',
    ]),
    inert: raw.inert === true,
  };
}
