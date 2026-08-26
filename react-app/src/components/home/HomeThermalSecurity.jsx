import { motion } from 'motion/react';
import { Activity, Flame, ShieldCheck } from 'lucide-react';

import GlassCard from '../glass/GlassCard';

const thermalZones = [
  { label: 'React build', value: 'stable', load: 72 },
  { label: 'API service', value: 'healthy', load: 64 },
  { label: 'Database', value: 'ready', load: 51 },
  { label: 'Deploy gate', value: 'staging', load: 86 },
];

const securityLogs = [
  ['06:41:43', 'Branch policy checked for visual feature branch', 'OK'],
  ['06:41:45', 'Secret values kept outside tracked files and logs', 'OK'],
  ['06:41:49', 'Staging cert path selected for repeat spinups', 'OK'],
  ['06:42:02', 'Production cert approval still required', 'HOLD'],
];

const HomeThermalSecurity = () => {
  return (
    <section
      className="home-obsidian-section home-thermal-security"
      data-testid="base2-thermal-security"
      aria-label="Base2 thermal telemetry and security logs"
    >
      <div className="home-thermal-grid">
        <div data-testid="base2-thermal-dynamics">
          <GlassCard className="home-thermal-panel">
            <div className="home-panel-title home-panel-title-hot">
              <Flame className="w-5 h-5" aria-hidden="true" />
              <span>Thermal Dynamics</span>
            </div>
            <div className="home-thermal-zone-grid">
              {thermalZones.map((zone, index) => (
                <div className="home-thermal-zone" key={zone.label}>
                  <span>{zone.label}</span>
                  <strong>{zone.value}</strong>
                  <div className="home-thermal-meter">
                    <motion.i
                      initial={{ width: 0 }}
                      whileInView={{ width: `${zone.load}%` }}
                      viewport={{ once: true }}
                      transition={{ delay: index * 0.08, duration: 0.6 }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>
        </div>

        <div data-testid="base2-security-logs">
          <GlassCard className="home-security-log-panel">
            <div className="home-security-heading">
              <div className="home-panel-title home-panel-title-secure">
                <ShieldCheck className="w-5 h-5" aria-hidden="true" />
                <span>Security Logs</span>
              </div>
              <div className="home-secure-pill">Status: Secure</div>
            </div>
            <div className="home-security-log-list">
              {securityLogs.map(([time, event, status]) => (
                <div className="home-security-log-row" key={`${time}-${event}`}>
                  <span>{time}</span>
                  <strong>{event}</strong>
                  <em data-state={status.toLowerCase()}>{status}</em>
                </div>
              ))}
            </div>
          </GlassCard>
        </div>
      </div>

      <div data-testid="base2-seismic-monitoring">
        <GlassCard className="home-seismic-panel">
          <div className="home-panel-title home-panel-title-seismic">
            <Activity className="w-5 h-5" aria-hidden="true" />
            <span>Seismic Monitoring</span>
          </div>
          <div
            className="home-seismic-bars"
            role="img"
            aria-label="Base2 workflow activity monitor"
          >
            {Array.from({ length: 28 }).map((_, index) => (
              <motion.span
                key={index}
                initial={{ height: '18%' }}
                animate={{ height: `${26 + ((index * 17) % 58)}%` }}
                transition={{
                  duration: 1.2,
                  repeat: Infinity,
                  repeatType: 'reverse',
                  delay: index * 0.035,
                }}
              />
            ))}
          </div>
        </GlassCard>
      </div>
    </section>
  );
};

export default HomeThermalSecurity;
