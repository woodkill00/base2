import React from 'react';
import { Link } from 'react-router-dom';

const HomeFooter = () => {
  return (
    <footer aria-label="Footer" className="glass" style={styles.footer}>
      <nav aria-label="Footer links" style={styles.links}>
        <Link to="/signup" style={styles.link}>
          Create account
        </Link>
        <Link to="/login" style={styles.link}>
          Sign in
        </Link>
      </nav>
      <div aria-label="Social" style={styles.social}>
        <span aria-label="Twitter" role="img">
          <svg
            role="img"
            aria-label="Twitter"
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M20 7.5c-.6.3-1.3.5-2 .6.7-.4 1.2-1 1.5-1.8-.7.4-1.4.7-2.2.8a3.3 3.3 0 00-5.6 3c-2.7-.1-5-1.4-6.6-3.4-.9 1.6-.5 3.6 1 4.7-.6 0-1.1-.2-1.6-.4 0 1.9 1.4 3.5 3.2 3.9-.5.1-1.1.1-1.6 0 .4 1.6 1.9 2.7 3.6 2.7A6.7 6.7 0 014 18.3a9.4 9.4 0 005.1 1.5c6.1 0 9.5-5.2 9.5-9.7v-.4c.6-.5 1.1-1.1 1.4-1.7z"
              stroke="currentColor"
              strokeWidth="1.4"
              strokeLinejoin="round"
            />
          </svg>
        </span>
        <span aria-label="GitHub" role="img">
          <svg
            role="img"
            aria-label="GitHub"
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M9 19c-4 1.5-4-2-5-2m10 4v-3c0-.9.3-1.6.9-2-3 0-6-.6-6-4a4 4 0 011-2.7 3.6 3.6 0 01.1-2.7s.8-.3 2.8 1a9.3 9.3 0 015 0c2-1.3 2.8-1 2.8-1 .2.9.2 1.9.1 2.7A4 4 0 0120 12c0 3.4-3 4-6 4 .6.4 1 1.2 1 2.3v3"
              stroke="currentColor"
              strokeWidth="1.4"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
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
  link: { textDecoration: 'none', color: '#fff' },
  social: { display: 'flex', gap: '0.75rem' },
};

export default HomeFooter;
