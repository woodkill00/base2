import { useMemo, useState } from 'react';
import { siteManifest } from '../../config/siteRuntime';
import { createAnalyticsController } from '../../services/privacyRuntime';
import ConsentBanner from './ConsentBanner';

const PrivacyRuntime = () => {
  const controller = useMemo(
    () =>
      createAnalyticsController({
        manifest: siteManifest,
        storage: window.localStorage,
        loadAdapter: () => {},
      }),
    []
  );
  const [decision] = useState(() => controller.start());
  return (
    <ConsentBanner
      manifest={siteManifest}
      initialDecision={decision}
      onDecision={(value) => controller.decide(value)}
    />
  );
};

export default PrivacyRuntime;
