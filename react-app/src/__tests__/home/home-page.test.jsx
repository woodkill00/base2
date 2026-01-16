import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import HomeHero from '../../components/home/HomeHero';
import HomeFeatures from '../../components/home/HomeFeatures';
import HomeVisual from '../../components/home/HomeVisual';
import HomeTrust from '../../components/home/HomeTrust';
import HomeFooter from '../../components/home/HomeFooter';
import { axe, toHaveNoViolations } from 'jest-axe';
import TestMemoryRouter from '../../test/TestMemoryRouter';

expect.extend(toHaveNoViolations);

describe('Public Home Page components', () => {
  test('render sections and keyboard focus', async () => {
    render(
      <TestMemoryRouter>
        <main>
          <HomeHero />
          <HomeFeatures />
          <HomeVisual />
          <HomeTrust />
          <HomeFooter />
        </main>
      </TestMemoryRouter>
    );

    expect(screen.getByRole('heading', { name: /Build Better with/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Everything You Need/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Beautiful by Design/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Privacy First/i })).toBeInTheDocument();
    expect(screen.getByRole('contentinfo', { name: /Footer/i })).toBeInTheDocument();

    const results = await axe(document.body);
    expect(results).toHaveNoViolations();
  });
});
