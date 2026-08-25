import { motion } from 'motion/react';
import { Layers } from 'lucide-react';

import GlassCard from '../glass/GlassCard';
import { siteManifest } from '../../config/siteRuntime';

const HomeFeatures = ({ items }) => {
  const features =
    items && items.length
      ? items
      : siteManifest.modules
          .filter((item) => item.enabled)
          .map((item) => ({
            icon: Layers,
            title: item.id.charAt(0).toUpperCase() + item.id.slice(1),
            description: `Enabled capability using contract version ${item.version}.`,
          }));

  return (
    <section
      id="features"
      style={{ padding: 'calc(4rem) calc(max(1rem, calc((100vw - 1200px) / 2))) calc(4rem)' }}
    >
      <div className="text-center mb-12">
        <h2 style={{ fontSize: 'clamp(1.875rem, 4vw, 2.5rem)', marginBottom: 'calc(1rem)' }}>
          Enabled Capabilities
        </h2>
        <p className="text-foreground/70 dark:text-foreground/60 max-w-2xl mx-auto">
          This site exposes only the capabilities selected by its reviewed manifest.
        </p>
      </div>

      <div
        className="grid gap-6"
        style={{
          gridTemplateColumns: 'repeat(auto-fit, minmax(calc(280px), 1fr))',
          maxWidth: '1200px',
          margin: '0 auto',
        }}
      >
        {features.map((feature, index) => {
          const Icon = feature.icon;
          return (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.1, duration: 0.5, ease: 'easeOut' }}
            >
              <GlassCard
                hover
                style={{
                  padding: 'calc(2.5rem) calc(2rem)',
                  height: '100%',
                }}
              >
                <div className="flex flex-col gap-4 h-full">
                  <div className="inline-flex items-center justify-center w-12 h-12 rounded-[var(--radius-lg)] backdrop-blur-2xl bg-white/25 dark:bg-black/40 border border-white/30 dark:border-white/20 shadow-[0_4px_16px_0_rgba(31,38,135,0.1)] dark:shadow-[0_4px_16px_0_rgba(0,0,0,0.3)]">
                    <Icon className="w-6 h-6 text-violet-400" aria-hidden="true" />
                  </div>
                  <h3 className="text-xl">{feature.title}</h3>
                  <p className="text-foreground/70 dark:text-foreground/60 text-sm leading-relaxed">
                    {feature.description}
                  </p>
                </div>
              </GlassCard>
            </motion.div>
          );
        })}
      </div>
    </section>
  );
};

export default HomeFeatures;
