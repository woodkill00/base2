import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import HomeHero from '../../components/home/HomeHero';
import HomeFeatures from '../../components/home/HomeFeatures';
import HomeVisual from '../../components/home/HomeVisual';
import HomeTrust from '../../components/home/HomeTrust';
import HomeFooter from '../../components/home/HomeFooter';
import { axe, toHaveNoViolations } from 'jest-axe';

expect.extend(toHaveNoViolations);

describe('Public Home Page components', () => {
  test('render sections and keyboard focus', async () => {
    render(
      <div>
        <HomeHero />
        <HomeFeatures />
        <HomeVisual />
        <HomeTrust />
        <HomeFooter />
      </div>
    );

    expect(screen.getByRole('heading', { name: /Elegant Glass Interface/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /What You Get/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Visual/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Trusted Values/i })).toBeInTheDocument();
    expect(screen.getByRole('contentinfo', { name: /Footer/i })).toBeInTheDocument();

    const results = await axe(document.body);
    expect(results).toHaveNoViolations();
  });
});
