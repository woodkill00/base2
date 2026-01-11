import React from 'react';
import HomeHero from '../../components/home/HomeHero';
import HomeFeatures from '../../components/home/HomeFeatures';
import HomeVisual from '../../components/home/HomeVisual';
import HomeTrust from '../../components/home/HomeTrust';
import HomeFooter from '../../components/home/HomeFooter';

export default { title: 'Home/Page' };

export const HomePage = () => (
  <div style={{ padding: 16 }}>
    <HomeHero />
    <HomeFeatures />
    <HomeVisual />
    <HomeTrust />
    <HomeFooter />
  </div>
);
