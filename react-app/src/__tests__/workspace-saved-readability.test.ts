import { expect, test, vi } from 'vitest';
import { measureSavedInspector, savedLabelFits } from '../../e2e/workspace/saved-readability';

test('a contained narrow button or selector cannot certify full label readability', () => {
  expect(savedLabelFits({ available: 24, required: 107 })).toBe(false);
  expect(savedLabelFits({ available: 59.4, required: 78.78647 })).toBe(false);
  expect(savedLabelFits({ available: 108, required: 120 })).toBe(false);
  expect(savedLabelFits({ available: 212, required: 120 })).toBe(true);
});

const measure = (
  width: string,
  required: number,
  boxSizing = 'border-box',
  scale = 1,
  padding = 24,
  fragmentCount = 1,
  textRight?: number,
  fragmentStep = 24
) => {
  const card = document.createElement('div');
  card.id = 'workspace-detail';
  const panel = document.createElement('div');
  panel.innerHTML =
    [
      'Secure file',
      'Secure file',
      'Add relationship',
      'Submit for review',
      'Publish',
      'Delete record',
    ]
      .map((name) => `<button>${name}</button>`)
      .join('') +
    '<label><span>Relationship field</span><select><option>Related articles</option></select></label><input type="file"><input type="file">';
  card.append(panel);
  document.body.append(card);
  const style = {
    width,
    boxSizing,
    paddingLeft: `${padding}px`,
    paddingRight: `${padding}px`,
    borderLeftWidth: '1px',
    borderRightWidth: '1px',
    font: '16px sans-serif',
    fontSize: '16px',
    fontWeight: '400',
    lineHeight: '24px',
    fontFamily: 'PRIVATE font string must not be exported',
    letterSpacing: 'normal',
    transform: `scale(${scale})`,
    zoom: String(scale),
  } as CSSStyleDeclaration;
  vi.spyOn(window, 'getComputedStyle').mockReturnValue(style);
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({
    font: '',
    measureText: () => ({ width: required }),
  } as unknown as CanvasRenderingContext2D);
  const textRect = {
    x: 0,
    y: 0,
    left: 0,
    top: 0,
    right: textRight ?? required * scale,
    bottom: 20,
    width: required * scale,
    height: 20,
  } as DOMRect;
  vi.spyOn(document, 'createRange').mockReturnValue({
    selectNodeContents: vi.fn(),
    getClientRects: () =>
      Array.from({ length: fragmentCount }, (_, index) => ({
        ...textRect,
        top: index * fragmentStep,
        bottom: index * fragmentStep + 20,
      })),
    getBoundingClientRect: () => textRect,
  } as unknown as Range);
  for (const button of Array.from(panel.querySelectorAll('button'))) {
    Object.defineProperty(button, 'clientWidth', { value: Math.round(parseFloat(width) - 2) });
    vi.spyOn(button, 'getBoundingClientRect').mockReturnValue({
      width: parseFloat(width) * scale,
      height: 44,
      x: 0,
      y: 0,
      top: 0,
      bottom: 44,
      left: 0,
      right: parseFloat(width) * scale,
    } as DOMRect);
  }
  try {
    return measureSavedInspector(panel);
  } finally {
    card.remove();
    vi.restoreAllMocks();
  }
};

test.each([
  ['compact', '110.21875px', 64.012619, 22.1, 63.8],
  ['desktop', '145.359375px', 95.357605, 24, 95],
])(
  '%s intrinsic Secure file width retains fractional content space',
  (_, width, required, padding, roundedAvailable) => {
    expect(Math.round(parseFloat(width as string) - 2) - 2 * (padding as number)).toBe(
      roundedAvailable
    );
    const result = measure(width as string, required as number, 'border-box', 1, padding as number);
    expect(result.labels.filter((row) => row.label === 'Secure file').map(savedLabelFits)).toEqual([
      true,
      true,
    ]);
    expect(result.counts).toEqual({
      'Secure file': 2,
      'Add relationship': 1,
      'Submit for review': 1,
      Publish: 1,
      'Delete record': 1,
      relationship: 1,
      files: 2,
    });
    expect(result.labels).toHaveLength(9);
  }
);

test('fractional measurement still rejects a real subpixel deficit', () => {
  expect(savedLabelFits(measure('145.25px', 95.357605).labels[0])).toBe(false);
  expect(savedLabelFits({ available: 64.00300000000001, required: 64.01261901855469 })).toBe(false);
});

test('real row space fits without accepting wrapped or escaped rendered text', () => {
  expect(savedLabelFits(measure('200px', 64.012619).labels[0])).toBe(true);
  expect(savedLabelFits(measure('200px', 64.012619, 'border-box', 1, 24, 2).labels[0])).toBe(false);
  expect(savedLabelFits(measure('200px', 64.012619, 'border-box', 1, 24, 1, 201).labels[0])).toBe(
    false
  );
  expect(savedLabelFits(measure('200px', 64.012619, 'border-box', 1, 24, 0).labels[0])).toBe(false);
  expect(
    savedLabelFits(measure('200px', 64.012619, 'border-box', 1, 24, 2, undefined, 0).labels[0])
  ).toBe(true);
});

test('failure geometry is fixed-schema numeric data with bounded fragments and no CSS text', () => {
  const result = measure('200px', 64.012619, 'border-box', 1, 24, 30);
  const diagnostic = result.labels[0].diagnostic as Record<string, unknown>;
  expect(Object.keys(diagnostic).sort()).toEqual(
    [
      'schemaVersion',
      'layoutWidth',
      'boxSizing',
      'padding',
      'borders',
      'fontSize',
      'fontWeight',
      'lineHeight',
      'letterSpacing',
      'canvasAdvance',
      'clientWidth',
      'scrollWidth',
      'borderRect',
      'textRect',
      'fragmentCount',
      'fragments',
      'fragmentsTruncated',
    ].sort()
  );
  expect(diagnostic.fragments).toHaveLength(8);
  expect(diagnostic.fragmentCount).toBe(30);
  expect(diagnostic.fragmentsTruncated).toBe(true);
  expect(result.labels.filter((row) => row.diagnostic)).toHaveLength(2);
  expect(JSON.stringify(result.labels)).not.toContain('PRIVATE');
  expect(new TextEncoder().encode(JSON.stringify(result.labels)).length).toBeLessThan(8192);
  expect(
    (measure('Infinity', 64).labels[0].diagnostic as Record<string, unknown>).layoutWidth
  ).toBeNull();
});

test.each([0.5, 1.25, 2, 4])(
  'scale/zoom %s does not mix rendered pixels with layout text metrics',
  (scale) => {
    expect(measure('145.359375px', 95.357605, 'border-box', scale).labels[0].available).toBe(
      95.359375
    );
  }
);

test('content-box width already excludes padding and borders; invalid width fails closed', () => {
  expect(measure('95.359375px', 95.357605, 'content-box').labels[0].available).toBe(95.359375);
  expect(savedLabelFits(measure('auto', 95.357605).labels[0])).toBe(false);
});

test('label fit fails closed for missing or invalid measurements', () => {
  for (const row of [
    { available: NaN, required: 20 },
    { available: 200, required: NaN },
    { available: Infinity, required: 20 },
    { available: 200, required: 0 },
  ])
    expect(savedLabelFits(row)).toBe(false);
});
