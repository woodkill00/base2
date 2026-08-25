import { useState } from 'react';
import { motion } from 'motion/react';
import { Globe2, Layers3, Search, ShieldCheck, Sparkles } from 'lucide-react';
import GlassCard from '../glass/GlassCard';
import GlassButton from '../glass/GlassButton';
import GlassInput from '../glass/GlassInput';
import { siteManifest } from '../../config/siteRuntime';

const systemSignals = [
  {
    label: 'Modules',
    value: String(siteManifest.modules.filter((item) => item.enabled).length),
    icon: Layers3,
  },
  { label: 'Locales', value: String(siteManifest.locales.length), icon: Globe2 },
  { label: 'Profile', value: siteManifest.operationsProfile, icon: ShieldCheck },
];

const HomeHero = ({ onPrimary, onSecondary, onSearch }) => {
  const [query, setQuery] = useState('');

  return (
    <section
      className="home-obsidian-hero relative flex items-center justify-center"
      data-testid="manifest-home-hero"
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

          <div className="home-hero-layout relative z-10">
            <div className="home-hero-copy">
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.2, duration: 0.5, ease: 'easeOut' }}
                className="home-obsidian-eyebrow inline-flex items-center gap-2"
              >
                <Sparkles className="w-4 h-4" aria-hidden="true" />
                <span className="text-sm">{siteManifest.brand.theme} foundation</span>
              </motion.div>

              <motion.h1
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3, duration: 0.6, ease: 'easeOut' }}
                style={{ fontSize: 'clamp(2rem, 5vw, 3.5rem)', lineHeight: '1.2' }}
              >
                Build Better with <span className="home-obsidian-title">{siteManifest.name}</span>
              </motion.h1>

              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.4, duration: 0.6, ease: 'easeOut' }}
                className="text-foreground/70 dark:text-foreground/60 max-w-2xl"
                style={{ fontSize: 'clamp(1rem, 2vw, 1.25rem)' }}
              >
                {siteManifest.brand.voice}
              </motion.p>

              <motion.form
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5, duration: 0.6, ease: 'easeOut' }}
                style={{ width: 'calc(min(100%, 600px))' }}
                role="search"
                onSubmit={(event) => {
                  event.preventDefault();
                  if (siteManifest.search.enabled && query.trim().length >= 2)
                    onSearch(query.trim());
                }}
              >
                <GlassInput
                  id="hero-search"
                  label={undefined}
                  name="heroSearch"
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder={`Search ${siteManifest.name}...`}
                  icon={<Search className="w-5 h-5" />}
                  className="text-lg"
                  disabled={!siteManifest.search.enabled}
                />
                {!siteManifest.search.enabled && (
                  <p className="text-sm">Search is not enabled for this site.</p>
                )}
              </motion.form>

              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.6, duration: 0.6, ease: 'easeOut' }}
                className="flex flex-wrap gap-4"
                style={{ marginTop: 'calc(1rem)' }}
              >
                <GlassButton variant="primary" onClick={onPrimary}>
                  {siteManifest.contact.enabled ? 'Contact us' : 'Explore'}
                </GlassButton>
                <GlassButton variant="ghost" onClick={onSecondary}>
                  Accessibility
                </GlassButton>
              </motion.div>
            </div>

            <motion.aside
              initial={{ opacity: 0, x: 18 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.45, duration: 0.7, ease: 'easeOut' }}
              className="home-command-stack"
              aria-label="Site profile summary"
            >
              <div className="home-command-topline">
                <span>Site profile</span>
                <strong>{siteManifest.siteId}</strong>
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
            </motion.aside>
          </div>
        </GlassCard>
      </motion.div>
    </section>
  );
};
export default HomeHero;
