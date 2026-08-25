import { useAuth } from '../contexts/AuthContext';
import AppShell from '../components/glass/AppShell';
import GlassCard from '../components/glass/GlassCard';
import Navigation from '../components/Navigation';
import { siteManifest } from '../config/siteRuntime';

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

        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-tight">Available capabilities</h2>
          <GlassCard>
            <ul className="p-6">
              {siteManifest.modules
                .filter((item) => item.enabled)
                .map((item) => (
                  <li key={item.id}>{item.id}</li>
                ))}
            </ul>
          </GlassCard>
        </section>
      </div>
    </AppShell>
  );
};

export default Dashboard;
