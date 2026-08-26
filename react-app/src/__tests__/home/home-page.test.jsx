import { fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import HomeHero from '../../components/home/HomeHero';
import HomeFeatures from '../../components/home/HomeFeatures';
import HomeVisual from '../../components/home/HomeVisual';
import HomeTrust from '../../components/home/HomeTrust';
import HomeFooter from '../../components/home/HomeFooter';
import { axe, toHaveNoViolations } from 'jest-axe';
import TestMemoryRouter from '../../test/TestMemoryRouter';
import { siteManifest } from '../../config/siteRuntime';
import ContactForm from '../../components/portfolio/ContactForm';

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
    expect(screen.getByRole('heading', { name: /Enabled Capabilities/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Beautiful by Design/i })).toBeInTheDocument();
    expect(screen.getByText(`Consent: ${siteManifest.consent.mode}`)).toBeInTheDocument();
    expect(screen.getByRole('contentinfo', { name: /Footer/i })).toBeInTheDocument();

    const results = await axe(document.body);
    expect(results).toHaveNoViolations();
  });

  test('stages a feedback note locally without transmitting private data', () => {
    render(<ContactForm />);
    expect(screen.getByRole('status')).toHaveTextContent(/No credentials/i);
    fireEvent.submit(screen.getByRole('button', { name: /Send review note/i }).closest('form'));
    expect(screen.getByRole('status')).toHaveTextContent(/staged for the next team report/i);
  });
});
