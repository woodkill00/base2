import AppShell from '../components/glass/AppShell';
import Navigation from '../components/Navigation';
import GlassCard from '../components/glass/GlassCard';

const Users = () => {
  return (
    <AppShell headerTitle="Users">
      <div className="mx-auto max-w-6xl px-4 py-8 space-y-6">
        <Navigation />

        <GlassCard>
          <div className="p-6">
            <h2 className="text-xl font-semibold tracking-tight">Users</h2>
            <p className="mt-2 text-sm opacity-80">This page is deprecated.</p>
          </div>
        </GlassCard>
      </div>
    </AppShell>
  );
};

export default Users;
