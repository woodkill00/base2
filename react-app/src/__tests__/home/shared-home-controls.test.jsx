import { fireEvent, render, screen } from '@testing-library/react';
import { vi, beforeEach, afterEach } from 'vitest';
import HomeSharedControls from '../../components/home/HomeSharedControls';

const originalScroll = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'scrollIntoView');
beforeEach(() =>
  Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
    configurable: true,
    value: vi.fn(),
  })
);
afterEach(() => {
  if (originalScroll)
    Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', originalScroll);
  else delete HTMLElement.prototype.scrollIntoView;
});

test('shared Home retains section actions, inline palette, safe utilities and movement toggle', () => {
  const onNavigate = vi.fn();
  const onUtilityAction = vi.fn();
  render(<HomeSharedControls onNavigate={onNavigate} onUtilityAction={onUtilityAction} />);
  fireEvent.click(screen.getByRole('button', { name: 'Features', exact: true }));
  expect(onNavigate).toHaveBeenCalledWith('features');
  fireEvent.keyDown(window, { key: 'k', ctrlKey: true });
  expect(screen.getByRole('region', { name: 'Base2 command palette' })).toBeVisible();
  fireEvent.click(screen.getByTestId('base2-color-scheme-basalt'));
  expect(screen.getByTestId('base2-color-scheme-basalt')).toHaveAttribute('aria-pressed', 'true');
  expect(screen.getByRole('button', { name: /Admin diagnostics/ })).toBeDisabled();
  fireEvent.keyDown(window, { key: 'Escape' });
  expect(screen.queryByRole('region')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('checkbox', { name: /movement/i }));
  expect(screen.queryByTestId('shared-home-movement')).not.toBeInTheDocument();
});
