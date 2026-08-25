import { Navigate, useLocation } from 'react-router-dom';

const PermissionRoute = ({ user, permission, children }) => {
  const location = useLocation();
  const permissions = Array.isArray(user?.permissions) ? user.permissions : [];

  if (!permission || permissions.includes(permission)) return children;

  return (
    <Navigate
      to="/account"
      replace
      state={{ deniedPath: location.pathname, reason: 'permission_required' }}
    />
  );
};

export default PermissionRoute;
