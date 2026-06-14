import { useState } from 'react';
import { motion } from 'motion/react';
import { Activity, Layers, Search, ShieldCheck, Sparkles } from 'lucide-react';
import GlassCard from '../glass/GlassCard';
import GlassButton from '../glass/GlassButton';
import GlassInput from '../glass/GlassInput';

const systemSignals = [
  { label: 'API-ready', value: 'Django + React', icon: Layers },
  { label: 'Protected', value: 'Auth flows kept', icon: ShieldCheck },
  { label: 'Observable', value: 'Health checks live', icon: Activity },
];

const HomeHero = ({ onPrimary, onSecondary }) => {
  const [query, setQuery] = useState('');

  return (
    <section
      className="home-obsidian-hero relative flex items-center justify-center"
      data-testid="base2-preserved-home-hero"
      style={{
        minHeight: 'calc(100vh - 3.5rem - 1px)',
        padding: 'calc(2rem) calc(max(1rem, calc((100vw - 1200px) / 2)))',
      }}
    >
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: 'easeOut' }}
        style={{ width: 'calc(min(100%, 1080px))' }}
      >
        <GlassCard
          className="home-obsidian-panel relative overflow-hidden"
          style={{ padding: 'calc(clamp(2.5rem, 6vw, 5rem)) calc(clamp(1.5rem, 5vw, 4rem))' }}
        >
          <div className="home-obsidian-grid" aria-hidden="true" />

          <div className="relative z-10 grid items-center gap-8 lg:grid-cols-[1.12fr_0.88fr]">
            <div className="flex flex-col items-start text-left" style={{ gap: 'calc(1.25rem)' }}>
              <motion.div
                initial={{ opacity: 0, scale: 0.96 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.2, duration: 0.5, ease: 'easeOut' }}
                className="home-obsidian-eyebrow inline-flex items-center gap-2"
              >
                <Sparkles className="w-4 h-4" aria-hidden="true" />
                <span className="text-sm">Base2 visual system upgrade</span>
              </motion.div>

              <motion.h1
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3, duration: 0.6, ease: 'easeOut' }}
                style={{ fontSize: 'clamp(2.4rem, 5vw, 4.6rem)', lineHeight: '1.04' }}
              >
                Build Better with
                <br />
                <span className="home-obsidian-title">Base2</span>
              </motion.h1>

              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.4, duration: 0.6, ease: 'easeOut' }}
                className="text-foreground/75 dark:text-foreground/70 max-w-2xl"
                style={{ fontSize: 'clamp(1rem, 2vw, 1.18rem)' }}
              >
                The existing Base2 app keeps its auth, API, deployment, and dashboard workflows,
                now with a darker command-center surface inspired by the volcanic obsidian reference.
              </motion.p>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5, duration: 0.6, ease: 'easeOut' }}
                style={{ width: 'calc(min(100%, 620px))' }}
              >
                <GlassInput
                  id="hero-search"
                  label={undefined}
                  name="heroSearch"
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search Base2 docs, APIs, and workflows..."
                  icon={<Search className="w-5 h-5" />}
                  className="text-lg"
                />
              </motion.div>

              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.6, duration: 0.6, ease: 'easeOut' }}
                className="flex flex-wrap gap-4"
                style={{ marginTop: 'calc(0.5rem)' }}
              >
                <GlassButton variant="primary" onClick={onPrimary} className="home-cta-primary">
                  Get Started
                </GlassButton>
                <GlassButton variant="ghost" onClick={onSecondary}>
                  View Documentation
                </GlassButton>
              </motion.div>
            </div>

            <motion.div
              initial={{ opacity: 0, x: 18 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.45, duration: 0.7, ease: 'easeOut' }}
              className="home-command-stack"
              data-testid="base2-visual-command-stack"
            >
              <div className="home-command-topline">
                <span>Base2 runtime</span>
                <strong>preserved</strong>
              </div>
              {systemSignals.map((signal) => {
                const Icon = signal.icon;
                return (
                  <div className="home-command-row" key={signal.label}>
                    <Icon className="w-5 h-5" aria-hidden="true" />
                    <div>
                      <span>{signal.label}</span>
                      <strong>{signal.value}</strong>
                    </div>
                  </div>
                );
              })}
            </motion.div>
          </div>
        </GlassCard>
      </motion.div>
    </section>
  );
};
export default HomeHero;
