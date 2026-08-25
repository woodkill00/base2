import { useState } from 'react';
import GlassButton from '../glass/GlassButton';

const ConsentBanner = ({ manifest, initialDecision, onDecision }) => {
  const [decision, setDecision] = useState(initialDecision);
  if (manifest.consent.mode !== 'opt-in' || !manifest.analytics.enabled || decision !== 'unset')
    return null;
  const choose = (value) => setDecision(onDecision(value) || value);
  return (
    <section
      role="region"
      aria-label="Privacy choices"
      className="fixed bottom-4 left-4 right-4 z-50 glass"
      style={{ padding: '1rem', maxWidth: 760, margin: '0 auto' }}
    >
      <h2>Privacy choices</h2>
      <p>Optional analytics stay off unless you choose to allow them.</p>
      <div className="flex gap-3">
        <GlassButton type="button" variant="ghost" onClick={() => choose('rejected')}>
          Use essential only
        </GlassButton>
        {manifest.analytics.enabled && (
          <GlassButton type="button" variant="primary" onClick={() => choose('granted')}>
            Allow analytics
          </GlassButton>
        )}
      </div>
    </section>
  );
};

export default ConsentBanner;
