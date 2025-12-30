import { render, screen } from '@testing-library/react';
import ErrorBoundary from '../components/ErrorBoundary.jsx';

function Boom() {
  throw new Error('boom');
}

test('ErrorBoundary renders fallback on error', () => {
  render(
    <ErrorBoundary>
      <Boom />
    </ErrorBoundary>
  );
  expect(screen.getByRole('alert')).toBeInTheDocument();
  expect(screen.getByText(/Something went wrong/i)).toBeInTheDocument();
});
