import React from 'react';

const OAuthCallback = () => {
  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>OAuth callback not used</h1>
        <div style={styles.error}>
          This app uses Google Sign-In (ID token) on the login page.
        </div>
      </div>
    </div>
  );
};

const styles = {
  container: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '24px',
  },
  card: {
    width: '100%',
    maxWidth: '420px',
    background: 'white',
    borderRadius: '12px',
    padding: '24px',
    border: '1px solid #e5e7eb',
  },
  title: {
    margin: '0 0 12px 0',
  },
  error: {
    padding: '10px 12px',
    background: '#fee2e2',
    color: '#991b1b',
    borderRadius: '8px',
    fontSize: '14px',
  },
};

export default OAuthCallback;
