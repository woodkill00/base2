import React from 'react';
import { render, screen } from '@testing-library/react';
import GlassButton from '../components/glass/GlassButton';

describe('GlassButton extra coverage', () => {
  test('applies custom className and onClick', () => {
    const onClick = jest.fn();
    render(
      <GlassButton className="extra-class" onClick={onClick}>
        Click Me
      </GlassButton>
    );
    const btn = screen.getByRole('button', { name: 'Click Me' });
    expect(btn.className).toContain('extra-class');
    btn.click();
    expect(onClick).toHaveBeenCalled();
  });
});
