import { Navigate, useLocation } from 'react-router-dom';

import { useAuth } from '../contexts/AuthContext';

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
        }}
      >
        <div>Loading...</div>
      </div>
    );
  }

  if (isAuthenticated) return children;

  const next = `${location.pathname}${location.search || ''}`;
  return <Navigate to={`/login?next=${encodeURIComponent(next)}`} replace />;
};

export default ProtectedRoute;
