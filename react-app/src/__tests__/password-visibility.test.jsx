import { fireEvent, render, screen } from '@testing-library/react';
import { useState } from 'react';
import GlassInput from '../components/glass/GlassInput';

function Form({ type = 'password', disabled = false, submit = () => {} }) {
  const [value, setValue] = useState('Synthetic-only-42');
  return (
    <form onSubmit={submit}>
      <GlassInput
        id="secret"
        label="Password"
        name="password"
        type={type}
        value={value}
        onChange={(event) => setValue(event.target.value)}
        disabled={disabled}
        autoComplete="current-password"
        ariaInvalid="true"
        ariaDescribedBy="problem"
      />
      <span id="problem">Example error</span>
      <button type="button">Outside</button>
    </form>
  );
}

test('password reveal preserves value, attributes and input node without submitting', () => {
  const submit = vi.fn();
  render(<Form submit={submit} />);
  const field = screen.getByLabelText('Password', { exact: true });
  expect(field).toHaveAttribute('type', 'password');
  const toggle = screen.getByRole('button', { name: 'Show password' });
  expect(toggle).toHaveAttribute('aria-controls', 'secret');
  fireEvent.click(toggle);
  expect(screen.getByLabelText('Password', { exact: true })).toBe(field);
  expect(field).toHaveAttribute('type', 'text');
  expect(field).toHaveValue('Synthetic-only-42');
  expect(field).toHaveAttribute('autocomplete', 'current-password');
  expect(field).toHaveAttribute('aria-describedby', 'problem');
  expect(field).toHaveAttribute('aria-invalid', 'true');
  expect(toggle).toHaveAttribute('aria-pressed', 'true');
  fireEvent.click(screen.getByRole('button', { name: 'Hide password' }));
  expect(field).toHaveAttribute('type', 'password');
  expect(submit).not.toHaveBeenCalled();
});

test('leaving the control hides a revealed password', () => {
  render(<Form />);
  fireEvent.click(screen.getByRole('button', { name: 'Show password' }));
  const field = screen.getByLabelText('Password', { exact: true });
  fireEvent.blur(field, { relatedTarget: screen.getByRole('button', { name: 'Outside' }) });
  expect(field).toHaveAttribute('type', 'password');
});

test('non-password inputs have no visibility control', () => {
  render(<Form type="email" />);
  expect(screen.queryByRole('button', { name: /Show password/ })).not.toBeInTheDocument();
});

test('disabled fields cannot be revealed or edited', () => {
  render(<Form disabled />);
  expect(screen.getByLabelText('Password', { exact: true })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Show password' })).toBeDisabled();
});

test('pointer activation preserves focus and moving within the control keeps visibility', () => {
  render(<Form />);
  const field = screen.getByLabelText('Password', { exact: true });
  field.focus();
  const toggle = screen.getByRole('button', { name: 'Show password' });
  expect(fireEvent.pointerDown(toggle)).toBe(false);
  expect(field).toHaveFocus();
  fireEvent.click(toggle);
  fireEvent.blur(field, { relatedTarget: toggle });
  expect(field).toHaveAttribute('type', 'text');
});
