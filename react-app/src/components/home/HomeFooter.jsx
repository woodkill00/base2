import React from 'react';

const HomeFooter = () => {
  return (
    <footer aria-label="Footer" className="glass" style={styles.footer}>
      <nav aria-label="Footer links" style={styles.links}>
        <a href="#" style={styles.link}>
          Docs
        </a>
        <a href="#" style={styles.link}>
          Privacy
        </a>
        <a href="#" style={styles.link}>
          Terms
        </a>
      </nav>
      <div aria-label="Social" style={styles.social}>
        <span aria-label="Twitter" role="img">
          🐦
        </span>
        <span aria-label="GitHub" role="img">
          💻
        </span>
      </div>
    </footer>
  );
};

const styles = {
  footer: {
    height: 'var(--footer-h)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0 16px',
  },
  links: { display: 'flex', gap: '1rem' },
  link: { textDecoration: 'none' },
  social: { display: 'flex', gap: '0.75rem' },
};

export default HomeFooter;
