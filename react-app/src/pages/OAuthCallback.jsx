import AppShell from '../components/glass/AppShell';
import GlassCard from '../components/glass/GlassCard';

const OAuthCallback = () => {
  return (
    <AppShell variant="public" headerTitle="OAuth">
      <div className="mx-auto max-w-md px-4 py-10">
        <GlassCard>
          <div className="p-6 space-y-3">
            <h1 className="text-xl font-semibold tracking-tight">OAuth callback not used</h1>
            <p className="text-sm opacity-80">
              This app uses Google Sign-In (ID token) on the login page.
            </p>
          </div>
        </GlassCard>
      </div>
    </AppShell>
  );
};

export default OAuthCallback;
