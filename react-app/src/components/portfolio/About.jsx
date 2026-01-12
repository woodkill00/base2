import React from 'react';
import { motion } from 'framer-motion';
import { fadeUpBlur } from '../../lib/motion';
import GlassCard from '../glass/GlassCard';

const About = () => {
  return (
    <section aria-labelledby="about-title" style={styles.section}>
      <motion.div
        initial={fadeUpBlur.initial}
        animate={fadeUpBlur.animate}
        transition={fadeUpBlur.transition}
      >
        <h2 id="about-title" style={styles.title}>
          About
        </h2>
        <GlassCard>
          <div style={styles.container}>
            <div style={styles.avatarWrap} aria-hidden="true">
              <div style={styles.avatar} className="glass" />
            </div>
            <div style={styles.content}>
              <p style={styles.text}>
                I’m Woodkill Dev — building clean, accessible, and modern interfaces with a focus on
                performance, motion, and glassmorphism aesthetics.
              </p>
              <div style={styles.skillsWrap}>
                <div role="list" aria-label="Skills" style={styles.skillsList}>
                  {['React', 'TypeScript', 'Tailwind', 'Framer Motion', 'A11y', 'Jest/RTL'].map(
                    (s) => (
                      <span
                        role="listitem"
                        key={s}
                        className="glass glass-pill"
                        style={styles.skill}
                      >
                        {s}
                      </span>
                    )
                  )}
                </div>
              </div>
            </div>
          </div>
        </GlassCard>
      </motion.div>
    </section>
  );
};

const styles = {
  section: { padding: 'var(--space) 1rem' },
  title: { textAlign: 'center', marginBottom: 'var(--space)' },
  container: {
    display: 'grid',
    gap: 'var(--space)',
    gridTemplateColumns: '1fr',
    alignItems: 'center',
  },
  avatarWrap: { display: 'flex', justifyContent: 'center' },
  avatar: {
    width: 'clamp(96px, 20vw, 140px)',
    height: 'clamp(96px, 20vw, 140px)',
    borderRadius: '9999px',
  },
  content: { display: 'grid', gap: 'calc(var(--space) * 0.75)' },
  text: { margin: 0, opacity: 0.9 },
  skillsWrap: { overflowX: 'auto' },
  skillsList: { display: 'flex', gap: '0.75rem', padding: '0.25rem', alignItems: 'center' },
  skill: { padding: '0.4rem 0.8rem', whiteSpace: 'nowrap' },
};

export default About;
