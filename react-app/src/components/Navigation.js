import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const Navigation = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  const isActive = (path) => location.pathname === path;

  return (
    <nav style={styles.nav} aria-label="App navigation">
      <div style={styles.container}>
        <Link to="/dashboard" style={styles.logo}>
          <span style={styles.logoIcon}>🚀</span>
          Base2
        </Link>

        <div style={styles.menu}>
          <Link
            to="/dashboard"
            style={{
              ...styles.menuItem,
              ...(isActive('/dashboard') && styles.menuItemActive),
            }}
          >
            Dashboard
          </Link>
          <Link
            to="/settings"
            style={{
              ...styles.menuItem,
              ...(isActive('/settings') && styles.menuItemActive),
            }}
          >
            Settings
          </Link>
        </div>

        <div style={styles.userSection}>
          <div style={styles.userInfo}>
            <img
              src={user?.avatar_url || user?.picture || 'https://via.placeholder.com/40'}
              alt="Profile"
              style={styles.avatar}
            />
            <span style={styles.userName}>{user?.display_name || user?.name || user?.email}</span>
          </div>
          <button onClick={handleLogout} style={styles.logoutButton}>
            Logout
          </button>
        </div>
      </div>
    </nav>
  );
};

const styles = {
  nav: {
    background: 'white',
    borderBottom: '1px solid #e0e0e0',
    boxShadow: '0 2px 4px rgba(0, 0, 0, 0.05)',
    position: 'sticky',
    top: 0,
    zIndex: 1000,
  },
  container: {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '15px 20px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  logo: {
    fontSize: '24px',
    fontWeight: '700',
    color: '#667eea',
    textDecoration: 'none',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  logoIcon: {
    fontSize: '28px',
  },
  menu: {
    display: 'flex',
    gap: '20px',
  },
  menuItem: {
    fontSize: '16px',
    fontWeight: '500',
    color: '#666',
    textDecoration: 'none',
    padding: '8px 16px',
    borderRadius: '6px',
    transition: 'all 0.2s',
  },
  menuItemActive: {
    color: '#667eea',
    background: '#f0f4ff',
  },
  userSection: {
    display: 'flex',
    alignItems: 'center',
    gap: '15px',
  },
  userInfo: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  avatar: {
    width: '40px',
    height: '40px',
    borderRadius: '50%',
    objectFit: 'cover',
    border: '2px solid #667eea',
  },
  userName: {
    fontSize: '14px',
    fontWeight: '600',
    color: '#333',
  },
  logoutButton: {
    padding: '8px 20px',
    fontSize: '14px',
    fontWeight: '600',
    color: '#666',
    background: '#f0f0f0',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
};

export default Navigation;
