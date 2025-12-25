import React from 'react';

import { useAuth } from '../contexts/AuthContext';
import Navigation from '../components/Navigation';

const Dashboard = () => {
  const { user } = useAuth();

  return (
    <div style={styles.container}>
      <Navigation />
      <div style={styles.content}>
        <div style={styles.header}>
          <h1 style={styles.title}>Dashboard</h1>
          <p style={styles.subtitle}>Welcome back, {user?.name || user?.display_name || ''}!</p>
          {user?.email ? <p style={styles.subtitle}>{user.email}</p> : null}
        </div>

        <div style={styles.grid}>
          <div style={styles.card}>
            <div style={styles.cardIcon}>📊</div>
            <h3 style={styles.cardTitle}>Statistics</h3>
            <p style={styles.cardValue}>24</p>
            <p style={styles.cardLabel}>Total Items</p>
          </div>

          <div style={styles.card}>
            <div style={styles.cardIcon}>👥</div>
            <h3 style={styles.cardTitle}>Users</h3>
            <p style={styles.cardValue}>1,234</p>
            <p style={styles.cardLabel}>Active Users</p>
          </div>

          <div style={styles.card}>
            <div style={styles.cardIcon}>📈</div>
            <h3 style={styles.cardTitle}>Growth</h3>
            <p style={styles.cardValue}>+12%</p>
            <p style={styles.cardLabel}>This Month</p>
          </div>

          <div style={styles.card}>
            <div style={styles.cardIcon}>⭐</div>
            <h3 style={styles.cardTitle}>Rating</h3>
            <p style={styles.cardValue}>4.8</p>
            <p style={styles.cardLabel}>Average Score</p>
          </div>
        </div>

        <div style={styles.section}>
          <h2 style={styles.sectionTitle}>Recent Activity</h2>
          <div style={styles.activityCard}>
            <div style={styles.activityList}>
              <div style={styles.activityItem}>
                <div style={styles.activityIcon}>🔵</div>
                <div style={styles.activityContent}>
                  <p style={styles.activityText}>You logged in successfully</p>
                  <p style={styles.activityTime}>Just now</p>
                </div>
              </div>
              <div style={styles.activityItem}>
                <div style={styles.activityIcon}>🟢</div>
                <div style={styles.activityContent}>
                  <p style={styles.activityText}>Profile updated</p>
                  <p style={styles.activityTime}>2 hours ago</p>
                </div>
              </div>
              <div style={styles.activityItem}>
                <div style={styles.activityIcon}>🟡</div>
                <div style={styles.activityContent}>
                  <p style={styles.activityText}>New feature available</p>
                  <p style={styles.activityTime}>1 day ago</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div style={styles.section}>
          <h2 style={styles.sectionTitle}>Quick Actions</h2>
          <div style={styles.actionGrid}>
            <button style={styles.actionButton}>
              <span style={styles.actionIcon}>📝</span>
              <span>Create New</span>
            </button>
            <button style={styles.actionButton}>
              <span style={styles.actionIcon}>📤</span>
              <span>Upload File</span>
            </button>
            <button style={styles.actionButton}>
              <span style={styles.actionIcon}>👥</span>
              <span>Invite User</span>
            </button>
            <button style={styles.actionButton}>
              <span style={styles.actionIcon}>📊</span>
              <span>View Reports</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

const styles = {
  container: {
    minHeight: '100vh',
    background: '#f5f7fa',
  },
  content: {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '20px',
  },
  header: {
    marginBottom: '30px',
  },
  title: {
    fontSize: '32px',
    fontWeight: '700',
    color: '#333',
    marginBottom: '5px',
  },
  subtitle: {
    fontSize: '16px',
    color: '#666',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
    gap: '20px',
    marginBottom: '30px',
  },
  card: {
    background: 'white',
    borderRadius: '12px',
    padding: '25px',
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
    textAlign: 'center',
    transition: 'transform 0.2s, box-shadow 0.2s',
    cursor: 'pointer',
  },
  cardIcon: {
    fontSize: '36px',
    marginBottom: '15px',
  },
  cardTitle: {
    fontSize: '14px',
    color: '#666',
    fontWeight: '600',
    marginBottom: '10px',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  cardValue: {
    fontSize: '32px',
    fontWeight: '700',
    color: '#667eea',
    marginBottom: '5px',
  },
  cardLabel: {
    fontSize: '14px',
    color: '#999',
  },
  section: {
    marginBottom: '30px',
  },
  sectionTitle: {
    fontSize: '24px',
    fontWeight: '700',
    color: '#333',
    marginBottom: '20px',
  },
  activityCard: {
    background: 'white',
    borderRadius: '12px',
    padding: '25px',
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
  },
  activityList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  activityItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '15px',
  },
  activityIcon: {
    fontSize: '24px',
  },
  activityContent: {
    flex: 1,
  },
  activityText: {
    fontSize: '16px',
    color: '#333',
    marginBottom: '5px',
  },
  activityTime: {
    fontSize: '14px',
    color: '#999',
  },
  actionGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '15px',
  },
  actionButton: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '10px',
    padding: '15px 20px',
    background: 'white',
    border: '2px solid #e0e0e0',
    borderRadius: '8px',
    fontSize: '16px',
    fontWeight: '600',
    color: '#333',
    cursor: 'pointer',
    transition: 'all 0.2s',
    boxShadow: '0 2px 4px rgba(0, 0, 0, 0.05)',
  },
  actionIcon: {
    fontSize: '20px',
  },
};

export default Dashboard;
