import React from 'react';
import GlassCard from '../glass/GlassCard';

const HomeFeatures = ({ items = defaultItems }) => {
  return (
    <section aria-labelledby="home-features-title" style={styles.section}>
      <h2 id="home-features-title" style={styles.sectionTitle}>
        What You Get
      </h2>
      <div style={styles.grid}>
        {items.map((it, idx) => (
          <GlassCard key={idx}>
            <div style={styles.cardContent} tabIndex={0} aria-label={it.title} role="article">
              <span aria-label={it.title + ' icon'} role="img" style={styles.icon}>
                {it.icon}
              </span>
              <h3 style={styles.title}>{it.title}</h3>
              <p style={styles.desc}>{it.description}</p>
            </div>
          </GlassCard>
        ))}
      </div>
    </section>
  );
};

const styles = {
  section: { padding: '2rem 1rem' },
  sectionTitle: { textAlign: 'center', marginBottom: '1rem' },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(calc(300px - 2rem), 1fr))',
    gap: '1rem',
  },
  cardContent: { display: 'grid', gap: '0.5rem' },
  icon: { display: 'inline-block', width: 24, height: 24 },
  title: { margin: 0 },
  desc: { margin: 0, opacity: 0.9 },
};

const defaultItems = [
  { title: 'Privacy-first', description: 'Respectful defaults and secure patterns', icon: '🔒' },
  { title: 'AI-native', description: 'Designed for intelligent interfaces', icon: '🤖' },
  { title: 'Open architecture', description: 'Composable and extendable UI', icon: '🧩' },
  { title: 'Built for scale', description: 'Responsive and robust', icon: '📈' },
];

export default HomeFeatures;
