import AppShell from '../glass/AppShell';
import GlassCard from '../glass/GlassCard';

// Preserve the approved two existing card densities; all account journeys now
// compose the same shell/card rather than maintaining independent wrappers.
export default function AuthPageFrame({ title, variant = 'public', compact = false, children }) {
  return (
    <AppShell variant={variant} headerTitle={title}>
      <div
        className={compact ? undefined : 'mx-auto max-w-md px-4 py-10'}
        style={compact ? { maxWidth: '480px', margin: '0 auto', padding: '20px' } : undefined}
      >
        <GlassCard>{children}</GlassCard>
      </div>
    </AppShell>
  );
}
