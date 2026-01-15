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
          <GlassCard key={idx} variant="subtle" interactive>
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

const Svg = ({ label, children }) => (
  <svg
    role="img"
    aria-label={label}
    viewBox="0 0 24 24"
    width="20"
    height="20"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    {children}
  </svg>
);

const styles = {
  section: { padding: '2rem 1rem' },
  sectionTitle: { textAlign: 'center', marginBottom: '1rem' },
  row: { display: 'flex', gap: '1rem', flexWrap: 'wrap', justifyContent: 'center' },
  pill: { display: 'flex', gap: '0.5rem', alignItems: 'center', padding: '0.5rem 1rem' },
  icon: { display: 'inline-block', width: 20, height: 20 },
};

const defaultItems = [
  {
    text: 'Privacy-first',
    icon: (
      <Svg label="Privacy-first">
        <path
          d="M12 2l7 4v6c0 5-3 9-7 10C8 21 5 17 5 12V6l7-4z"
          stroke="currentColor"
          strokeWidth="1.8"
        />
      </Svg>
    ),
  },
  {
    text: 'AI-native',
    icon: (
      <Svg label="AI-native">
        <path d="M8 8h8v8H8V8z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
      </Svg>
    ),
  },
  {
    text: 'Open architecture',
    icon: (
      <Svg label="Open architecture">
        <path
          d="M8 10l4-3 4 3v8H8v-8z"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinejoin="round"
        />
      </Svg>
    ),
  },
  {
    text: 'Built for scale',
    icon: (
      <Svg label="Built for scale">
        <path
          d="M6 16l4-4 3 3 5-6"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    ),
  },
];

export default HomeTrust;
