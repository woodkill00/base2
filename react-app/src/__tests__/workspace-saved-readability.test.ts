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
  padding = 24
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
    letterSpacing: 'normal',
    transform: `scale(${scale})`,
    zoom: String(scale),
  } as CSSStyleDeclaration;
  vi.spyOn(window, 'getComputedStyle').mockReturnValue(style);
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({
    font: '',
    measureText: () => ({ width: required }),
  } as unknown as CanvasRenderingContext2D);
  for (const button of Array.from(panel.querySelectorAll('button'))) {
    Object.defineProperty(button, 'clientWidth', { value: Math.round(parseFloat(width) - 2) });
    vi.spyOn(button, 'getBoundingClientRect').mockReturnValue({
      width: parseFloat(width) * scale,
      height: 44,
      left: 0,
      right: 0,
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
