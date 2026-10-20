import { fireEvent, render, screen } from '@testing-library/react';
import ToastProvider, { useToast } from '../components/ToastProvider';

function Controls() {
  const toast = useToast();
  return <button onClick={() => toast.success('Saved')}>Notify</button>;
}
test('notifications use theme tokens and a reachable dismiss control', () => {
  render(
    <ToastProvider>
      <Controls />
    </ToastProvider>
  );
  fireEvent.click(screen.getByRole('button', { name: 'Notify' }));
  const toast = screen.getByTestId('notification-toast');
  expect(toast.style.background).toBe('var(--color-surface)');
  expect(toast.style.color).toBe('var(--color-text)');
  expect(screen.getByRole('button', { name: 'Dismiss notification' })).toHaveStyle({
    minWidth: '44px',
    minHeight: '44px',
  });
  fireEvent.click(screen.getByRole('button', { name: 'Dismiss notification' }));
  expect(screen.queryByTestId('notification-toast')).not.toBeInTheDocument();
});
