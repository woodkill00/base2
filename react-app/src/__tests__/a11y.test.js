import { render } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import Login from '../pages/Login';
import Signup from '../pages/Signup';
import Dashboard from '../pages/Dashboard';
import Settings from '../pages/Settings';

expect.extend(toHaveNoViolations);

describe('Accessibility checks', () => {
  test('Login has no obvious a11y violations', async () => {
    const { container } = render(<Login />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  test('Signup has no obvious a11y violations', async () => {
    const { container } = render(<Signup />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  test('Dashboard has no obvious a11y violations', async () => {
    const { container } = render(<Dashboard />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  test('Settings has no obvious a11y violations', async () => {
    const { container } = render(<Settings />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
