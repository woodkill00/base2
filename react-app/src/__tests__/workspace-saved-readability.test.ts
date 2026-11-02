import { expect, test } from 'vitest';
import { savedLabelFits } from '../../e2e/workspace/saved-readability';

test('a contained narrow button or selector cannot certify full label readability', () => {
  expect(savedLabelFits({ available: 24, required: 107 })).toBe(false);
  expect(savedLabelFits({ available: 59.4, required: 78.78647 })).toBe(false);
  expect(savedLabelFits({ available: 108, required: 120 })).toBe(false);
  expect(savedLabelFits({ available: 212, required: 120 })).toBe(true);
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
