export type LabelMeasurement = {
  available: number;
  required: number;
  renderedLineCount?: number;
  renderedContained?: boolean;
};

export function savedLabelFits({
  available,
  required,
  renderedLineCount,
  renderedContained,
}: LabelMeasurement) {
  return (
    Number.isFinite(available) &&
    Number.isFinite(required) &&
    required > 0 &&
    available >= required &&
    (renderedLineCount === undefined || renderedLineCount === 1) &&
    renderedContained !== false
  );
}

// Executed in the synthetic selected inspector. Rectangle containment alone also
// accepts a tall, character-wrapped button; measure its complete authored label.
export function measureSavedInspector(panel: HTMLElement) {
  const card = document.querySelector('#workspace-detail')!.getBoundingClientRect();
  const bounds = panel.getBoundingClientRect();
  const breaches = [
    panel,
    ...Array.from(
      panel.querySelectorAll<HTMLElement>(
        'section,fieldset,form,label,input,select,textarea,button'
      )
    ),
  ].flatMap((node, index) => {
    const box = node.getBoundingClientRect();
    if (!box.width || !box.height) return [];
    return box.left < card.left - 1 ||
      box.right > card.right + 1 ||
      box.left < bounds.left - 1 ||
      box.right > bounds.right + 1 ||
      node.scrollWidth > node.clientWidth + 1
      ? [index]
      : [];
  });
  const canvas = document.createElement('canvas');
  const context = canvas.getContext('2d')!;
  const pixels = (value: string) => Number.parseFloat(value) || 0;
  const textWidth = (text: string, style: CSSStyleDeclaration) => {
    context.font = style.font;
    return (
      context.measureText(text).width + Math.max(0, text.length - 1) * pixels(style.letterSpacing)
    );
  };
  const contentWidth = (_node: HTMLElement, style: CSSStyleDeclaration) => {
    // clientWidth rounds to integer CSS pixels, which can reject an intact
    // intrinsic label. Resolved width preserves fractional layout pixels;
    // unlike a transformed DOMRect it stays in the canvas font's CSS units.
    const width = Number.parseFloat(style.width);
    if (!Number.isFinite(width)) return NaN;
    if (style.boxSizing === 'content-box') return width;
    if (style.boxSizing !== 'border-box') return NaN;
    return (
      width -
      pixels(style.borderLeftWidth) -
      pixels(style.borderRightWidth) -
      pixels(style.paddingLeft) -
      pixels(style.paddingRight)
    );
  };
  // Only fixed synthetic control names and bounded numeric geometry are emitted.
  // Never emit field values, file names, arbitrary text, selectors or CSS strings.
  const number = (value: number) =>
    Number.isFinite(value) && Math.abs(value) <= 1_000_000 ? value : null;
  const rectangle = (value: DOMRect) => [value.x, value.y, value.width, value.height].map(number);
  const labels: Array<LabelMeasurement & { label: string; diagnostic?: unknown }> = [];
  const names = [
    'Secure file',
    'Add relationship',
    'Submit for review',
    'Publish',
    'Delete record',
  ];
  const counts: Record<string, number> = {};
  for (const name of names) {
    const buttons = Array.from(panel.querySelectorAll<HTMLButtonElement>('button')).filter(
      (node) => node.textContent?.trim() === name
    );
    counts[name] = buttons.length;
    for (const node of buttons.slice(0, 2)) {
      const style = getComputedStyle(node);
      const range = document.createRange();
      range.selectNodeContents(node);
      const fragments = Array.from(range.getClientRects());
      // Inline descendants can contribute several rectangles on one line.
      const lines: Array<{ top: number; bottom: number }> = [];
      for (const rect of [...fragments].sort((a, b) => a.top - b.top)) {
        const last = lines[lines.length - 1];
        if (last && rect.top < last.bottom && rect.bottom > last.top) {
          last.top = Math.min(last.top, rect.top);
          last.bottom = Math.max(last.bottom, rect.bottom);
        } else lines.push({ top: rect.top, bottom: rect.bottom });
      }
      const borderRect = node.getBoundingClientRect();
      const textRect = range.getBoundingClientRect();
      const diagnostic = {
        schemaVersion: 1,
        layoutWidth: number(Number.parseFloat(style.width)),
        boxSizing:
          style.boxSizing === 'border-box'
            ? 'border-box'
            : style.boxSizing === 'content-box'
              ? 'content-box'
              : 'invalid',
        padding: [style.paddingTop, style.paddingRight, style.paddingBottom, style.paddingLeft].map(
          (value) => number(pixels(value))
        ),
        borders: [
          style.borderTopWidth,
          style.borderRightWidth,
          style.borderBottomWidth,
          style.borderLeftWidth,
        ].map((value) => number(pixels(value))),
        fontSize: number(Number.parseFloat(style.fontSize)),
        fontWeight: number(
          style.fontWeight === 'normal'
            ? 400
            : style.fontWeight === 'bold'
              ? 700
              : Number.parseFloat(style.fontWeight)
        ),
        lineHeight: number(Number.parseFloat(style.lineHeight)),
        letterSpacing: number(pixels(style.letterSpacing)),
        canvasAdvance: number(textWidth(name, style)),
        clientWidth: number(node.clientWidth),
        scrollWidth: number(node.scrollWidth),
        borderRect: rectangle(borderRect),
        textRect: rectangle(textRect),
        fragmentCount: number(fragments.length),
        fragments: fragments.slice(0, 8).map(rectangle),
        fragmentsTruncated: fragments.length > 8,
      };
      labels.push({
        label: name,
        available: contentWidth(node, style),
        required: textWidth(name, style),
        renderedLineCount: lines.length,
        renderedContained:
          textRect.left >= borderRect.left &&
          textRect.right <= borderRect.right &&
          textRect.top >= borderRect.top &&
          textRect.bottom <= borderRect.bottom,
        ...(diagnostic ? { diagnostic } : {}),
      });
    }
  }
  const select = Array.from(panel.querySelectorAll<HTMLSelectElement>('select')).find(
    (node) => node.closest('label')?.querySelector('span')?.textContent === 'Relationship field'
  );
  counts.relationship = select ? 1 : 0;
  if (select) {
    const style = getComputedStyle(select);
    labels.push({
      label: 'Relationship field',
      available: contentWidth(select, style) - 24,
      required: textWidth(select.selectedOptions[0].text, style),
    });
  }
  const files = Array.from(panel.querySelectorAll<HTMLInputElement>('input[type="file"]'));
  counts.files = files.length;
  for (const node of files.slice(0, 2)) {
    const style = getComputedStyle(node);
    const button = getComputedStyle(node, '::file-selector-button');
    // These three registered projects are Chromium/en-US. This necessary width
    // check covers its native Choose File button, not opaque filename/status text;
    // exact native saved-state screenshots remain required for pixel inspection.
    labels.push({
      label: 'Choose File',
      available: contentWidth(node, style),
      required:
        textWidth('Choose File', button) +
        pixels(button.paddingLeft) +
        pixels(button.paddingRight) +
        pixels(button.borderLeftWidth) +
        pixels(button.borderRightWidth),
    });
  }
  return { breaches, counts, labels };
}
