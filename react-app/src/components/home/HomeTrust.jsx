import React from 'react';
import GlassCard from '../glass/GlassCard';

const HomeTrust = ({ items = defaultItems }) => {
  return (
    <section aria-labelledby="home-trust-title" style={styles.section}>
      <h2 id="home-trust-title" style={styles.sectionTitle}>
        Trusted Values
      </h2>
      <div style={styles.row} role="list">
        {items.map((it, idx) => (
          <GlassCard key={idx}>
            <div style={styles.pill} tabIndex={0} role="listitem">
              <span aria-label={it.text + ' icon'} role="img" style={styles.icon}>
                {it.icon}
              </span>
              <span>{it.text}</span>
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
  row: { display: 'flex', gap: '1rem', flexWrap: 'wrap', justifyContent: 'center' },
  pill: { display: 'flex', gap: '0.5rem', alignItems: 'center', padding: '0.5rem 1rem' },
  icon: { display: 'inline-block', width: 20, height: 20 },
};

const defaultItems = [
  { text: 'Privacy-first', icon: '🔒' },
  { text: 'AI-native', icon: '🤖' },
  { text: 'Open architecture', icon: '🧩' },
  { text: 'Built for scale', icon: '📈' },
];

export default HomeTrust;
