import { render, screen } from '@testing-library/react';
import { ensureBackdropSupport } from '../services/glass/supports';

function GlassDiv() {
  return (
    <div data-testid="glass" className="glass">
      content
    </div>
  );
}

describe('Glass fallback when backdrop-filter unsupported', () => {
  afterEach(() => {
    document.documentElement.classList.remove('no-backdrop');
  });

  it('adds no-backdrop class to root when unsupported', () => {
    const original = global.CSS && global.CSS.supports;
    global.CSS = { supports: () => false };

    ensureBackdropSupport();

    render(<GlassDiv />);
    expect(document.documentElement.classList.contains('no-backdrop')).toBe(true);
    expect(screen.getByTestId('glass').classList.contains('glass')).toBe(true);

    // restore
    if (original) {
      global.CSS.supports = original;
    }
  });
});
