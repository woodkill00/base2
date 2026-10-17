import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import BoundGoogleLogin from '../components/BoundGoogleLogin';
import { authAPI } from '../services/api';

vi.mock('../services/api', () => ({ authAPI: { googleChallenge: vi.fn() } }));
vi.mock('@react-oauth/google', () => ({
  GoogleLogin: ({ nonce, onSuccess, onError }) => (
    <div>
      <button data-nonce={nonce} onClick={() => onSuccess({ credential: 'synthetic' })}>
        Google
      </button>
      <button onClick={onError}>Provider failure</button>
    </div>
  ),
}));

const valid = { nonce: 'n'.repeat(43), expires_in: 300 };
beforeEach(() => {
  vi.clearAllMocks();
  authAPI.googleChallenge.mockResolvedValue(valid);
});
afterEach(() => vi.useRealTimers());

test('provider receives nonce only after successful challenge; success consumes UI state', async () => {
  const success = vi.fn();
  render(<BoundGoogleLogin onSuccess={success} onError={vi.fn()} />);
  expect(screen.getByRole('status')).toHaveTextContent('Preparing');
  const button = await screen.findByRole('button', { name: 'Google' });
  expect(button).toHaveAttribute('data-nonce', valid.nonce);
  fireEvent.click(button);
  expect(success).toHaveBeenCalledWith({ credential: 'synthetic' });
  expect(screen.getByRole('button', { name: 'Retry Google sign-in' })).toBeInTheDocument();
  expect(authAPI.googleChallenge).toHaveBeenCalledTimes(1);
});

test.each([null, { nonce: 'bad', expires_in: 300 }, { nonce: 'n'.repeat(43), expires_in: 999 }])(
  'malformed challenge blocks provider and allows explicit retry',
  async (response) => {
    authAPI.googleChallenge.mockResolvedValueOnce(response).mockResolvedValue(valid);
    render(<BoundGoogleLogin onSuccess={vi.fn()} onError={vi.fn()} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Retry Google sign-in' }));
    expect(await screen.findByRole('button', { name: 'Google' })).toBeInTheDocument();
    expect(authAPI.googleChallenge).toHaveBeenCalledTimes(2);
  }
);

test('network rejection is visible without leaking response content or auto retry', async () => {
  authAPI.googleChallenge.mockRejectedValue(new Error('private provider body'));
  render(<BoundGoogleLogin onSuccess={vi.fn()} onError={vi.fn()} />);
  expect(await screen.findByRole('button', { name: 'Retry Google sign-in' })).toBeInTheDocument();
  expect(screen.queryByText(/private provider/)).not.toBeInTheDocument();
  expect(authAPI.googleChallenge).toHaveBeenCalledTimes(1);
});

test('provider error invalidates button and asks for explicit retry', async () => {
  const error = vi.fn();
  render(<BoundGoogleLogin onSuccess={vi.fn()} onError={error} />);
  fireEvent.click(await screen.findByRole('button', { name: 'Provider failure' }));
  expect(error).toHaveBeenCalledTimes(1);
  expect(screen.queryByRole('button', { name: 'Google' })).not.toBeInTheDocument();
});

test('expiry never leaves a usable provider button', async () => {
  vi.useFakeTimers();
  render(<BoundGoogleLogin onSuccess={vi.fn()} onError={vi.fn()} />);
  await act(async () => {
    await Promise.resolve();
  });
  expect(screen.getByRole('button', { name: 'Google' })).toBeInTheDocument();
  act(() => vi.advanceTimersByTime(300000));
  expect(screen.getByRole('button', { name: 'Retry Google sign-in' })).toBeInTheDocument();
  expect(authAPI.googleChallenge).toHaveBeenCalledTimes(1);
});

test('unmount aborts pending request', async () => {
  authAPI.googleChallenge.mockReturnValue(new Promise(() => {}));
  const { unmount } = render(<BoundGoogleLogin onSuccess={vi.fn()} onError={vi.fn()} />);
  await waitFor(() => expect(authAPI.googleChallenge).toHaveBeenCalledTimes(1));
  const signal = authAPI.googleChallenge.mock.calls[0][0];
  unmount();
  expect(signal.aborted).toBe(true);
});
