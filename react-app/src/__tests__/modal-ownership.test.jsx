import { acquireModalBackground } from '../components/glass/ModalOwnership';
import { expect, test } from 'vitest';

test('modal owners release out of order and restore authored inertness and stacking', () => {
  const root = document.createElement('div');
  root.style.isolation = 'auto';
  const first = acquireModalBackground(root),
    second = acquireModalBackground(root);
  expect(root.hasAttribute('inert')).toBe(true);
  expect(root.style.isolation).toBe('isolate');
  first();
  first();
  expect(root.hasAttribute('inert')).toBe(true);
  second();
  expect(root.hasAttribute('inert')).toBe(false);
  expect(root.style.isolation).toBe('auto');
  root.setAttribute('inert', '');
  const third = acquireModalBackground(root);
  third();
  expect(root.hasAttribute('inert')).toBe(true);
  expect(root.style.isolation).toBe('auto');
});
