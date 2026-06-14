import { motion } from 'motion/react';
import { Activity, Command, Database, GitBranch, LayoutGrid, LockKeyhole, Search, Server, Settings, Shield, Zap } from 'lucide-react';

import GlassCard from '../glass/GlassCard';

const bootLines = [
  'Load Base2 React shell',
  'Verify Django API link',
  'Mount protected dashboard routes',
  'Prime DigitalOcean staging checks',
];

const commandItems = [
  { label: 'Open signup flow', detail: 'public route preserved', icon: LockKeyhole },
  { label: 'Inspect API health', detail: '/api/health green', icon: Activity },
  { label: 'Review deploy logs', detail: 'staging droplet evidence', icon: Server },
];

const utilityItems = [LayoutGrid, Search, Shield, Database, GitBranch, Settings, Zap];

const HomeObsidianOps = () => {
  return (
    <section
      className="home-obsidian-section home-obsidian-ops"
      data-testid="base2-obsidian-ops"
      aria-label="Base2 obsidian operations console"
    >
      <div className="home-section-kicker">Obsidian control layer</div>
      <div className="home-obsidian-section-head">
        <div>
          <h2>Command Surface</h2>
          <p>
            The reference command palette, boot sequence, and utility rail are translated into Base2 controls,
            with live app workflows named directly instead of fictional system copy.
          </p>
        </div>
        <div className="home-obsidian-status-pill">
          <span />
          Visual sync active
        </div>
      </div>

      <div className="home-ops-grid">
        <div data-testid="base2-boot-sequence-panel"><GlassCard className="home-boot-panel">
          <div className="home-panel-title">
            <Command className="w-5 h-5" aria-hidden="true" />
            <span>Base2 boot sequence</span>
          </div>
          <div className="home-boot-lines">
            {bootLines.map((line, index) => (
              <motion.div
                key={line}
                className="home-boot-line"
                initial={{ opacity: 0, x: -8 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.08, duration: 0.35 }}
              >
                <span>[0{index + 1}]</span>
                <strong>{line}</strong>
              </motion.div>
            ))}
          </div>
          <div className="home-boot-progress" aria-label="Base2 boot readiness 100 percent">
            {[0, 1, 2, 3, 4, 5, 6, 7].map((item) => (
              <span key={item} />
            ))}
            <strong>100%</strong>
          </div>
        </GlassCard></div>

        <div data-testid="base2-command-palette-preview"><GlassCard className="home-command-palette-preview">
          <div className="home-command-search-row">
            <Search className="w-5 h-5" aria-hidden="true" />
            <span>Search Base2 commands...</span>
            <kbd>Ctrl K</kbd>
          </div>
          <div className="home-command-preview-list">
            {commandItems.map((item) => {
              const Icon = item.icon;
              return (
                <div className="home-command-preview-item" key={item.label}>
                  <Icon className="w-5 h-5" aria-hidden="true" />
                  <div>
                    <strong>{item.label}</strong>
                    <span>{item.detail}</span>
                  </div>
                  <em>Jump</em>
                </div>
              );
            })}
          </div>
        </GlassCard></div>

        <div data-testid="base2-utility-rail-preview"><GlassCard className="home-utility-rail-preview">
          <div className="home-utility-tab" aria-hidden="true" />
          <div className="home-panel-title">
            <Settings className="w-5 h-5" aria-hidden="true" />
            <span>Utility rail</span>
          </div>
          <div className="home-utility-icons" role="list" aria-label="Base2 utility shortcuts">
            {utilityItems.map((Icon, index) => (
              <div className="home-utility-icon" key={index} role="listitem">
                <Icon className="w-5 h-5" aria-hidden="true" />
              </div>
            ))}
          </div>
        </GlassCard></div>
      </div>
    </section>
  );
};

export default HomeObsidianOps;
