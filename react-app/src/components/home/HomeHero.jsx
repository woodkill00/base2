import React from 'react';
import { motion } from 'framer-motion';
import { fadeUpBlur } from '../../lib/motion';
import GlassCard from '../glass/GlassCard';
import GlassButton from '../glass/GlassButton';
import GlassInput from '../glass/GlassInput';

const HomeHero = ({
  title = 'Elegant Glass Interface',
  subtitle = 'Fast, accessible, and visually compelling UI system',
  primaryLabel = 'Get Started',
  secondaryLabel = 'Learn More',
  showInput = true,
}) => {
  return (
    <section aria-labelledby="home-hero-title" style={styles.section}>
      <GlassCard>
        <motion.div
          style={styles.heroContainer}
          initial={fadeUpBlur.initial}
          animate={fadeUpBlur.animate}
          transition={fadeUpBlur.transition}
        >
          <h1 id="home-hero-title" style={styles.title}>
            {title}
          </h1>
          <p style={styles.subtitle}>{subtitle}</p>
          <div style={styles.ctaRow}>
            <GlassButton variant="primary" className="glass-pill" onClick={() => {}}>
              {primaryLabel}
            </GlassButton>
            <GlassButton variant="secondary" onClick={() => {}}>
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
        </motion.div>
      </GlassCard>
    </section>
  );
};

const styles = {
  section: {
    display: 'flex',
    justifyContent: 'center',
    padding: 'var(--space) 1rem',
  },
  heroContainer: {
    minHeight: 'clamp(80vh, 100vh, 90vh)',
    width: 'min(calc(100% - var(--space)*2), 960px)',
    margin: '0 auto',
    textAlign: 'center',
    animation: 'heroFloat 10s ease-in-out infinite',
  },
  title: {
    fontSize: 'clamp(4rem, 10vw, 8rem)',
    margin: 0,
  },
  subtitle: {
    fontSize: 'clamp(0.875rem, 2vw + 0.5rem, 1.125rem)',
    opacity: 0.9,
  },
  ctaRow: {
    display: 'flex',
    gap: 'var(--space)',
    justifyContent: 'center',
    flexWrap: 'wrap',
    marginTop: 'var(--space)',
  },
};

export default HomeHero;
