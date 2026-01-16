import { useAuth } from '../contexts/AuthContext';
import AppShell from '../components/glass/AppShell';
import GlassCard from '../components/glass/GlassCard';
import GlassButton from '../components/glass/GlassButton';
import Navigation from '../components/Navigation';

const Dashboard = () => {
  const { user } = useAuth();

  return (
    <AppShell headerTitle="Dashboard">
      <div className="mx-auto max-w-6xl px-4 py-8 space-y-6">
        <Navigation />

        <GlassCard>
          <div className="p-6">
            <p className="text-sm opacity-80">
              Welcome back, {user?.name || user?.display_name || ''}!
            </p>
            {user?.email ? <p className="text-sm opacity-80">{user.email}</p> : null}
          </div>
        </GlassCard>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <GlassCard>
            <div className="p-6 space-y-2">
              <div className="text-3xl">📊</div>
              <h3 className="text-xs font-semibold tracking-wider uppercase opacity-80">
                Statistics
              </h3>
              <p className="text-3xl font-semibold tracking-tight">24</p>
              <p className="text-sm opacity-70">Total Items</p>
            </div>
          </GlassCard>

          <GlassCard>
            <div className="p-6 space-y-2">
              <div className="text-3xl">👥</div>
              <h3 className="text-xs font-semibold tracking-wider uppercase opacity-80">Users</h3>
              <p className="text-3xl font-semibold tracking-tight">1,234</p>
              <p className="text-sm opacity-70">Active Users</p>
            </div>
          </GlassCard>

          <GlassCard>
            <div className="p-6 space-y-2">
              <div className="text-3xl">📈</div>
              <h3 className="text-xs font-semibold tracking-wider uppercase opacity-80">Growth</h3>
              <p className="text-3xl font-semibold tracking-tight">+12%</p>
              <p className="text-sm opacity-70">This Month</p>
            </div>
          </GlassCard>

          <GlassCard>
            <div className="p-6 space-y-2">
              <div className="text-3xl">⭐</div>
              <h3 className="text-xs font-semibold tracking-wider uppercase opacity-80">Rating</h3>
              <p className="text-3xl font-semibold tracking-tight">4.8</p>
              <p className="text-sm opacity-70">Average Score</p>
            </div>
          </GlassCard>
        </div>

        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-tight">Recent Activity</h2>
          <GlassCard>
            <div className="p-6 space-y-4">
              <div className="flex items-center gap-3">
                <div className="text-2xl">🔵</div>
                <div>
                  <p className="text-sm">You logged in successfully</p>
                  <p className="text-xs opacity-70">Just now</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="text-2xl">🟢</div>
                <div>
                  <p className="text-sm">Profile updated</p>
                  <p className="text-xs opacity-70">2 hours ago</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="text-2xl">🟡</div>
                <div>
                  <p className="text-sm">New feature available</p>
                  <p className="text-xs opacity-70">1 day ago</p>
                </div>
              </div>
            </div>
          </GlassCard>
        </section>

        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-tight">Quick Actions</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <GlassButton
              variant="primary"
              className="w-full flex items-center justify-center gap-2"
            >
              <span className="text-lg">📝</span>
              <span>Create New</span>
            </GlassButton>
            <GlassButton
              variant="primary"
              className="w-full flex items-center justify-center gap-2"
            >
              <span className="text-lg">📤</span>
              <span>Upload File</span>
            </GlassButton>
            <GlassButton
              variant="primary"
              className="w-full flex items-center justify-center gap-2"
            >
              <span className="text-lg">👥</span>
              <span>Invite User</span>
            </GlassButton>
            <GlassButton
              variant="primary"
              className="w-full flex items-center justify-center gap-2"
            >
              <span className="text-lg">📊</span>
              <span>View Reports</span>
            </GlassButton>
          </div>
        </section>
      </div>
    </AppShell>
  );
};

export default Dashboard;
