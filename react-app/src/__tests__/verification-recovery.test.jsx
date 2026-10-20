import { act, fireEvent, render, screen } from '@testing-library/react';
import VerificationRecovery from '../components/auth/VerificationRecovery';
import { authAPI } from '../services/api';
vi.mock('../services/api');

test('requests the exact account alias and reports requested, not delivered', async () => {
  authAPI.resendVerification.mockResolvedValue({});
  render(<VerificationRecovery />);
  fireEvent.change(screen.getByLabelText('Account email'), {
    target: { value: 'person+test@example.test' },
  });
  await act(async () =>
    fireEvent.click(screen.getByRole('button', { name: 'Request verification email' }))
  );
  expect(authAPI.resendVerification).toHaveBeenCalledWith('person+test@example.test');
  expect(screen.getByRole('status')).toHaveTextContent('requested');
  expect(screen.getByLabelText('Account email')).toHaveValue('');
});
test('server limits produce actionable feedback without exposing backend detail', async () => {
  authAPI.resendVerification.mockRejectedValue({ status: 429, message: 'private detail' });
  render(<VerificationRecovery />);
  fireEvent.change(screen.getByLabelText('Account email'), {
    target: { value: 'person@example.test' },
  });
  await act(async () =>
    fireEvent.click(screen.getByRole('button', { name: 'Request verification email' }))
  );
  expect(screen.getByRole('alert')).toHaveTextContent('Please wait');
  expect(screen.queryByText('private detail')).not.toBeInTheDocument();
});
