import React from 'react';
import GlassCard from '../glass/GlassCard';

const ProjectCard = ({ title, description, tech = [] }) => {
  return (
    <GlassCard>
      <div style={styles.card} className="glass-interactive">
        <div style={styles.thumb} className="glass-strong" />
        <h3 style={styles.h3}>{title}</h3>
        <p style={styles.p}>{description}</p>
        <div style={styles.badges}>
          {tech.map((t) => (
            <span key={t} className="glass glass-pill" style={styles.badge}>
              {t}
            </span>
          ))}
        </div>
      </div>
    </GlassCard>
  );
};

const styles = {
  card: {
    display: 'grid',
    gap: '0.75rem',
    transition: 'transform 0.3s ease',
    willChange: 'transform',
  },
  thumb: { width: '100%', height: 'clamp(140px, 24vw, 200px)', borderRadius: 'var(--radius)' },
  h3: { margin: 0 },
  p: { margin: 0, opacity: 0.9 },
  badges: { display: 'flex', gap: '0.5rem', flexWrap: 'wrap' },
  badge: { padding: '0.35rem 0.7rem' },
};

export default ProjectCard;
