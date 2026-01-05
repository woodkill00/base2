import { useAuth } from '../contexts/AuthContext';
import AppShell from '../components/glass/AppShell';
import GlassCard from '../components/glass/GlassCard';
import GlassButton from '../components/glass/GlassButton';
import Navigation from '../components/Navigation';

const Dashboard = () => {
  const { user } = useAuth();

  return (
    <AppShell headerTitle="Dashboard">
      <div style={styles.content}>
        <Navigation />
        <GlassCard>
          <div style={styles.header}>
            <p style={styles.subtitle}>Welcome back, {user?.name || user?.display_name || ''}!</p>
            {user?.email ? <p style={styles.subtitle}>{user.email}</p> : null}
          </div>
        </GlassCard>

        <div style={styles.grid}>
          <GlassCard>
            <div style={styles.cardIcon}>📊</div>
            <h3 style={styles.cardTitle}>Statistics</h3>
            <p style={styles.cardValue}>24</p>
            <p style={styles.cardLabel}>Total Items</p>
          </GlassCard>

          <GlassCard>
            <div style={styles.cardIcon}>👥</div>
            <h3 style={styles.cardTitle}>Users</h3>
            <p style={styles.cardValue}>1,234</p>
            <p style={styles.cardLabel}>Active Users</p>
          </GlassCard>

          <GlassCard>
            <div style={styles.cardIcon}>📈</div>
            <h3 style={styles.cardTitle}>Growth</h3>
            <p style={styles.cardValue}>+12%</p>
            <p style={styles.cardLabel}>This Month</p>
          </GlassCard>

          <GlassCard>
            <div style={styles.cardIcon}>⭐</div>
            <h3 style={styles.cardTitle}>Rating</h3>
            <p style={styles.cardValue}>4.8</p>
            <p style={styles.cardLabel}>Average Score</p>
          </GlassCard>
        </div>

        <div style={styles.section}>
          <h2 style={styles.sectionTitle}>Recent Activity</h2>
          <GlassCard>
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
          </GlassCard>
        </div>

        <div style={styles.section}>
          <h2 style={styles.sectionTitle}>Quick Actions</h2>
          <div style={styles.actionGrid}>
            <GlassButton variant="primary">
              <span style={styles.actionIcon}>📝</span>
              <span>Create New</span>
            </GlassButton>
            <GlassButton variant="primary">
              <span style={styles.actionIcon}>📤</span>
              <span>Upload File</span>
            </GlassButton>
            <GlassButton variant="primary">
              <span style={styles.actionIcon}>👥</span>
              <span>Invite User</span>
            </GlassButton>
            <GlassButton variant="primary">
              <span style={styles.actionIcon}>📊</span>
              <span>View Reports</span>
            </GlassButton>
          </div>
        </div>
      </div>
    </AppShell>
  );
};

const styles = {
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
  actionIcon: {
    fontSize: '20px',
  },
};

export default Dashboard;
