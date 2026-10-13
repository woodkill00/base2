import { describe, expect, it, vi } from 'vitest';
import config from '../../tailwind.config.js';

describe('approved-design Tailwind compiler compatibility', () => {
  const utilities = () => {
    const addUtilities = vi.fn();
    config.plugins[0]({ addUtilities });
    return Object.assign({}, ...addUtilities.mock.calls.map(([rules]) => rules));
  };

  it('retains original glass styling and class-based dark preference', () => {
    expect(config.darkMode).toBe('class');
    expect(utilities()['.glass'].backdropFilter).toBe('blur(20px)');
    expect(utilities()['.glass-pill'].borderRadius).toBe('9999px');
  });

  it('uses v3 sibling margins instead of v4 last-child spacing', () => {
    const rule = utilities()['.space-y-4'];
    expect(Object.keys(rule)).toEqual(['& > :not([hidden]) ~ :not([hidden])']);
    expect(Object.values(rule)[0]).toEqual({
      '--tw-space-y-reverse': '0',
      marginTop: 'calc(1rem * calc(1 - var(--tw-space-y-reverse)))',
      marginBottom: 'calc(1rem * var(--tw-space-y-reverse))',
    });
  });

  it('preserves horizontal and reverse spacing for existing consumers', () => {
    const rules = utilities();
    expect(Object.values(rules['.space-x-1'])[0].marginLeft).toBe(
      'calc(0.25rem * calc(1 - var(--tw-space-x-reverse)))'
    );
    expect(Object.values(rules['.space-y-reverse'])[0]['--tw-space-y-reverse']).toBe('1');
    expect(Object.values(rules['.space-x-reverse'])[0]['--tw-space-x-reverse']).toBe('1');
  });
});
