import React from 'react';
import { useNavigate } from 'react-router-dom';

import AppShell from '../components/glass/AppShell';
import HomeHero from '../components/home/HomeHero';
import HomeFeatures from '../components/home/HomeFeatures';
import HomeVisual from '../components/home/HomeVisual';
import HomeTrust from '../components/home/HomeTrust';
import HomeFooter from '../components/home/HomeFooter';

const styles = {
  page: {
    minHeight: '100vh',
    backgroundColor: '#000',
    color: '#fff',
    display: 'flex',
    justifyContent: 'center',
    padding: '24px 16px',
  },
  containerInner: {
    maxWidth: '1200px',
    width: '100%',
    display: 'grid',
    gap: '24px',
  },
};

const Home = () => {
  const navigate = useNavigate();

  return (
    <AppShell variant="public" headerTitle="Home">
      <div className="gradient-background" aria-hidden="true" />
      <div style={styles.page} data-testid="home-page">
        <div style={styles.containerInner}>
          <HomeHero
            title="Build with glass"
            subtitle="A fast, accessible, calc-driven UI system with a modern app shell."
            primaryLabel="Create account"
            secondaryLabel="Sign in"
            onPrimary={() => navigate('/signup')}
            onSecondary={() => navigate('/login')}
          />
          <HomeFeatures />
          <HomeVisual />
          <HomeTrust />
          <HomeFooter />
        </div>
      </div>
    </AppShell>
  );
};

export default Home;
