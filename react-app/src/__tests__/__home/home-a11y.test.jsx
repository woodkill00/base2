import { render } from '@testing-library/react';
import TestMemoryRouter from '../../test/TestMemoryRouter';
import { axe, toHaveNoViolations } from 'jest-axe';

import Home from '../../pages/Home';

expect.extend(toHaveNoViolations);

describe('Home page accessibility', () => {
  test('has no obvious axe violations', async () => {
    const { container } = render(
      <TestMemoryRouter>
        <Home />
      </TestMemoryRouter>
    );

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
