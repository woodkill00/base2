import React from 'react';
import GlassCard from '../glass/GlassCard';
import GlassButton from '../glass/GlassButton';
import GlassInput from '../glass/GlassInput';

const HomeHero = ({
  title = 'Elegant Glass Interface',
  subtitle = 'Fast, accessible, and visually compelling UI system',
  primaryLabel = 'Get Started',
  secondaryLabel = 'Learn More',
  showInput = true,
  onPrimary,
  onSecondary,
}) => {
  return (
    <section aria-labelledby="home-hero-title" style={styles.section}>
      <GlassCard variant="elevated" interactive>
        <div className="home-hero-float" style={styles.heroContainer}>
          <h1 id="home-hero-title" style={styles.title}>
            {title}
          </h1>
          <p style={styles.subtitle}>{subtitle}</p>
          <div style={styles.ctaRow}>
            <GlassButton className="home-cta-primary" variant="primary" onClick={onPrimary}>
              {primaryLabel}
            </GlassButton>
            <GlassButton variant="secondary" onClick={onSecondary}>
              {secondaryLabel}
            </GlassButton>
          </div>
          {showInput && (
            <div style={{ marginTop: 16 }}>
              <GlassInput
                id="hero-search"
                label="Search"
                name="heroSearch"
                type="text"
                value={''}
                onChange={() => {}}
                placeholder="Ask a question…"
              />
            </div>
          )}
        </div>
      </GlassCard>
    </section>
  );
};

const styles = {
  section: {
    display: 'flex',
    justifyContent: 'center',
    padding: '2rem 1rem',
  },
  heroContainer: {
    minHeight: 'calc(100vh * 0.5)',
    width: 'min(calc(100% - 4rem), 960px)',
    margin: '0 auto',
    textAlign: 'center',
  },
  title: {
    fontSize: 'clamp(2rem, 5vw, 3rem)',
    margin: 0,
  },
  subtitle: {
    fontSize: 'clamp(1rem, 2.5vw, 1.25rem)',
    opacity: 0.9,
  },
  ctaRow: {
    display: 'flex',
    gap: '1rem',
    justifyContent: 'center',
    flexWrap: 'wrap',
    marginTop: '1rem',
  },
};

export default HomeHero;
