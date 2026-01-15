import React from 'react';
import GlassCard from '../glass/GlassCard';

import heroSvg from '../../assets/hero.svg';

const HomeVisual = ({ src = heroSvg, alt = 'Abstract glass UI illustration' }) => {
  return (
    <section aria-labelledby="home-visual-title" style={styles.section}>
      <h2 id="home-visual-title" style={styles.sectionTitle}>
        Visual
      </h2>
      <GlassCard>
        <div style={styles.frame}>
          <img src={src} alt={alt} loading="lazy" style={styles.img} />
        </div>
      </GlassCard>
    </section>
  );
};

const styles = {
  section: { padding: '2rem 1rem' },
  sectionTitle: { textAlign: 'center', marginBottom: '1rem' },
  frame: { overflow: 'visible' },
  img: { width: '100%', height: 'auto' },
};

export default HomeVisual;
