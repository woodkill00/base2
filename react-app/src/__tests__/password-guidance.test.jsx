import { fireEvent, render, screen } from '@testing-library/react';
import GlassInput from '../components/glass/GlassInput';
import PasswordRequirements from '../components/auth/PasswordRequirements';

test('creation guidance starts neutral then reports actual policy requirements', () => {
  const { rerender } = render(<PasswordRequirements value="" />);
  expect(screen.queryByText(/Needed:/)).not.toBeInTheDocument();
  rerender(<PasswordRequirements value="a" />);
  expect(screen.getAllByRole('listitem')[2]).toHaveTextContent('Met: A lowercase letter');
  expect(screen.getAllByRole('listitem')[0]).toHaveTextContent('Needed: At least 8 characters');
  rerender(<PasswordRequirements value="Synthetic123" />);
  expect(screen.queryByText(/Needed:/)).not.toBeInTheDocument();
  expect(screen.getAllByText(/Met:/)).toHaveLength(4);
});
test('Caps Lock guidance is linked to password input and clears on blur', () => {
  render(
    <GlassInput id="test-password" type="password" label="Password" value="" onChange={() => {}} />
  );
  const field = screen.getByLabelText('Password', { exact: true });
  fireEvent.keyDown(field, { key: 'A', modifierCapsLock: true });
  expect(screen.getByRole('status')).toHaveTextContent('Caps Lock is on');
  expect(field).toHaveAttribute('aria-describedby', 'test-password-caps-lock');
  fireEvent.keyUp(field, { key: 'CapsLock', modifierCapsLock: false });
  expect(screen.queryByRole('status')).not.toBeInTheDocument();
  fireEvent.keyDown(field, { key: 'A', modifierCapsLock: true });
  fireEvent.blur(field);
  expect(screen.queryByRole('status')).not.toBeInTheDocument();
});

test('ordinary text fields do not show password Caps Lock guidance', () => {
  render(<GlassInput id="plain" label="Name" value="" onChange={() => {}} />);
  const field = screen.getByLabelText('Name');
  fireEvent.keyDown(field, { key: 'A', modifierCapsLock: true });
  fireEvent.keyUp(field, { key: 'A', modifierCapsLock: true });
  expect(screen.queryByRole('status')).not.toBeInTheDocument();
});
