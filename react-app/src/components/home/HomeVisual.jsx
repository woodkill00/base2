import { motion } from 'motion/react';

import GlassCard from '../glass/GlassCard';

const signalRows = [
  ['Auth', 'login / signup / protected dashboard'],
  ['API', 'Django health and user workflows'],
  ['Deploy', 'DigitalOcean scripts and checks'],
];

const HomeVisual = () => {
  return (
    <section
      data-testid="base2-preserved-home-visual"
      style={{ padding: 'calc(4rem) calc(max(1rem, calc((100vw - 1200px) / 2))) calc(4rem)' }}
    >
      <div style={{ maxWidth: '1040px', margin: '0 auto' }}>
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        >
          <GlassCard className="home-visual-console" style={{ padding: 'calc(3rem) calc(2.5rem)', overflow: 'hidden' }}>
            <div className="text-center" style={{ marginBottom: 'calc(2rem)' }}>
              <h2 style={{ fontSize: 'clamp(1.875rem, 4vw, 2.5rem)', marginBottom: 'calc(1rem)' }}>
                Beautiful by Design
              </h2>
              <p className="text-foreground/70 dark:text-foreground/60">
                A Base2-native interface layer with volcanic contrast, readable glass, and tested workflows.
              </p>
            </div>

            <div className="home-runtime-frame" aria-label="Base2 runtime visual summary">
              <div className="home-runtime-header">
                <span>base2://dev-site</span>
                <strong>staging safe</strong>
              </div>
              <div className="home-runtime-grid">
                <div className="home-runtime-panel home-runtime-panel-primary">
                  <span>Visual layer</span>
                  <strong>Volcanic obsidian</strong>
                  <p>Sharper surfaces, calmer spacing, and responsive command-center contrast.</p>
                </div>
                <div className="home-runtime-panel">
                  <span>Product layer</span>
                  <strong>Base2 remains intact</strong>
                  <p>Routes, auth, API, dashboard, settings, scripts, and deployment flow stay wired.</p>
                </div>
                <div className="home-runtime-panel">
                  <span>Test layer</span>
                  <strong>Preservation gates</strong>
                  <p>Visual acceptance now checks that the result is still recognizably Base2.</p>
                </div>
              </div>
              <div className="home-runtime-rows">
                {signalRows.map(([label, value]) => (
                  <div className="home-runtime-row" key={label}>
                    <span>{label}</span>
                    <strong>{value}</strong>
                  </div>
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
