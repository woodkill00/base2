export type LabelMeasurement = { available: number; required: number };

export function savedLabelFits({ available, required }: LabelMeasurement) {
  return (
    Number.isFinite(available) && Number.isFinite(required) && required > 0 && available >= required
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
  const labels: Array<LabelMeasurement & { label: string }> = [];
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
    for (const node of buttons) {
      const style = getComputedStyle(node);
      labels.push({
        label: name,
        available: contentWidth(node, style),
        required: textWidth(name, style),
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
  for (const node of files) {
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
