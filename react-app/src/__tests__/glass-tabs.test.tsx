import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import GlassTabs from '../components/glass/GlassTabs';

describe('GlassTabs', () => {
  test('renders tabs and switches via keyboard', async () => {
    const user = userEvent.setup();
    const tabs = [
      { id: 'one', label: 'One' },
      { id: 'two', label: 'Two' },
    ];
    const onChange = jest.fn();
    render(<GlassTabs tabs={tabs} activeTab="one" onChange={onChange} />);

    const one = screen.getByRole('tab', { name: 'One' });
    const two = screen.getByRole('tab', { name: 'Two' });
    expect(one).toHaveAttribute('aria-selected', 'true');

    one.focus();
    await user.keyboard('{ArrowRight}');
    expect(onChange).toHaveBeenCalledWith('two');
    two.focus();
    await user.keyboard('{ArrowLeft}');
    expect(onChange).toHaveBeenCalledWith('one');
  });
});
