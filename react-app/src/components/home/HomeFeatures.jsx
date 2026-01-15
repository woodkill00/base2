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
          <GlassCard key={idx} variant="subtle" interactive>
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

const Svg = ({ label, children }) => (
  <svg
    role="img"
    aria-label={label}
    viewBox="0 0 24 24"
    width="24"
    height="24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    {children}
  </svg>
);

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
  {
    title: 'Privacy-first',
    description: 'Respectful defaults and secure patterns',
    icon: (
      <Svg label="Privacy-first">
        <path
          d="M12 2l7 4v6c0 5-3 9-7 10C8 21 5 17 5 12V6l7-4z"
          stroke="currentColor"
          strokeWidth="1.8"
        />
        <path
          d="M9.5 12a2.5 2.5 0 015 0v2.5h-5V12z"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinejoin="round"
        />
      </Svg>
    ),
  },
  {
    title: 'AI-native',
    description: 'Designed for intelligent interfaces',
    icon: (
      <Svg label="AI-native">
        <path d="M8 8h8v8H8V8z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
        <path
          d="M12 6v2m0 8v2M6 12h2m8 0h2"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
        />
      </Svg>
    ),
  },
  {
    title: 'Open architecture',
    description: 'Composable and extendable UI',
    icon: (
      <Svg label="Open architecture">
        <path
          d="M8 10l4-3 4 3v8H8v-8z"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinejoin="round"
        />
        <path d="M10 18v-5h4v5" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
      </Svg>
    ),
  },
  {
    title: 'Built for scale',
    description: 'Responsive and robust',
    icon: (
      <Svg label="Built for scale">
        <path
          d="M6 16l4-4 3 3 5-6"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path d="M6 18h12" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      </Svg>
    ),
  },
];

export default HomeFeatures;
