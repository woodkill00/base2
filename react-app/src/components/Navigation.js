import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import GlassButton from './glass/GlassButton';

const Navigation = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  const isActive = (path) => location.pathname === path;

  const linkClass = (path) =>
    [
      'text-sm font-medium px-3 py-2 rounded-[var(--radius-lg)] transition-all duration-300 ease-out',
      'hover:bg-white/20 dark:hover:bg-black/30',
      isActive(path) ? 'bg-white/20 dark:bg-black/30' : 'opacity-80 hover:opacity-100',
    ].join(' ');

  return (
    <nav aria-label="App navigation" className="sticky top-[calc(var(--nav-h)+0px)] z-40">
      <div className="mx-auto max-w-6xl px-4 pt-4">
        <div
          className={[
            'backdrop-blur-2xl border rounded-[var(--radius-lg)] transition-all duration-300 ease-out',
            'shadow-[0_8px_32px_0_rgba(31,38,135,0.15)] dark:shadow-[0_8px_32px_0_rgba(0,0,0,0.4)] dark:shadow-[0_0_40px_0_rgba(139,92,246,0.1)]',
            'bg-white/25 dark:bg-black/40 border-white/30 dark:border-white/20',
            'px-4 py-3',
          ].join(' ')}
        >
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center justify-between gap-3">
              <Link to="/dashboard" className="flex items-center gap-2">
                <span className="text-xl" aria-hidden="true">
                  🚀
                </span>
                <span className="text-sm font-semibold tracking-tight">Base2</span>
              </Link>
            </div>

            <div className="flex items-center gap-2">
              <Link to="/dashboard" className={linkClass('/dashboard')}>
                Dashboard
              </Link>
              <Link to="/settings" className={linkClass('/settings')}>
                Settings
              </Link>
            </div>

            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <img
                  src={user?.avatar_url || user?.picture || 'https://via.placeholder.com/40'}
                  alt="Profile"
                  className="w-9 h-9 rounded-full object-cover border border-white/30 dark:border-white/20"
                />
                <span className="text-sm opacity-90">
                  {user?.display_name || user?.name || user?.email}
                </span>
              </div>
              <GlassButton
                type="button"
                variant="ghost"
                className="text-sm px-4 py-2"
                onClick={handleLogout}
              >
                Logout
              </GlassButton>
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navigation;
