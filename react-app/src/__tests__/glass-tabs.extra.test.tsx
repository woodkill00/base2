import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import GlassTabs from '../components/glass/GlassTabs';

describe('GlassTabs extra coverage', () => {
  test('handles boundary keys and click', async () => {
    const user = userEvent.setup();
    const tabs = [
      { id: 'one', label: 'One' },
      { id: 'two', label: 'Two' },
      { id: 'three', label: 'Three' },
    ];
    const onChange = jest.fn();
    render(<GlassTabs tabs={tabs} activeTab="two" onChange={onChange} className="extra" />);

    const first = screen.getByRole('tab', { name: 'One' });
    const second = screen.getByRole('tab', { name: 'Two' });
    const last = screen.getByRole('tab', { name: 'Three' });

    // Click path
    last.click();
    expect(onChange).toHaveBeenCalledWith('three');

    // Boundary: left at first stays first
    first.focus();
    await user.keyboard('{ArrowLeft}');
    expect(onChange).toHaveBeenCalledWith('one');

    // Boundary: right at last stays last
    last.focus();
    await user.keyboard('{ArrowRight}');
    expect(onChange).toHaveBeenCalledWith('three');

    // Non-handled key is a no-op (ensures conditional branches fully covered)
    onChange.mockClear();
    second.focus();
    await user.keyboard('x');
    expect(onChange).not.toHaveBeenCalled();

    // aria-selected true/false states appear
    expect(first).toHaveAttribute('aria-selected', 'false');
    expect(second).toHaveAttribute('aria-selected', 'true');
    expect(last).toHaveAttribute('aria-selected', 'false');
  });
});
