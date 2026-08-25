import { motion } from 'motion/react';

import GlassCard from '../glass/GlassCard';
import { siteManifest } from '../../config/siteRuntime';

const HomeVisual = () => {
  return (
    <section
      style={{ padding: 'calc(4rem) calc(max(1rem, calc((100vw - 1200px) / 2))) calc(4rem)' }}
    >
      <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        >
          <GlassCard
            className="home-visual-console"
            style={{ padding: 'calc(3rem) calc(2.5rem)', overflow: 'hidden' }}
          >
            <div className="text-center" style={{ marginBottom: 'calc(2rem)' }}>
              <h2 style={{ fontSize: 'clamp(1.875rem, 4vw, 2.5rem)', marginBottom: 'calc(1rem)' }}>
                Beautiful by Design
              </h2>
              <p className="text-foreground/70 dark:text-foreground/60">
                A manifest-driven surface with deterministic, local visual assets.
              </p>
            </div>

            <div
              className="home-runtime-frame"
              role="region"
              tabIndex={0}
              aria-label="Enabled site modules"
            >
              <div className="home-runtime-header">
                <span>{siteManifest.siteId}</span>
                <strong>{siteManifest.defaultLocale}</strong>
              </div>
              <div className="home-runtime-grid">
                {siteManifest.modules
                  .filter((item) => item.enabled)
                  .map((item) => (
                    <article className="home-runtime-panel" key={item.id}>
                      <span>Enabled module</span>
                      <strong>{item.id}</strong>
                      <p>Contract version {item.version}</p>
                    </article>
                  ))}
              </div>
            </div>
          </GlassCard>
        </motion.div>
      </div>
    </section>
  );
};

export default HomeVisual;
