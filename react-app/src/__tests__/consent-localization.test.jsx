import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import ConsentBanner from '../components/public/ConsentBanner';
import {
  createAnalyticsController,
  localizedPath,
  resolveLocale,
} from '../services/privacyRuntime';
import { siteManifest } from '../config/siteRuntime';

const memoryStorage = () => {
  const values = new Map();
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
  };
};

describe('consent and localization policy', () => {
  it('never loads analytics before opt-in and loads at most once after consent', () => {
    const loadAdapter = vi.fn();
    const storage = memoryStorage();
    const manifest = { ...siteManifest, analytics: { enabled: true, provider: 'adapter' } };
    const controller = createAnalyticsController({ manifest, storage, loadAdapter });
    controller.start();
    expect(loadAdapter).not.toHaveBeenCalled();
    controller.decide('rejected');
    expect(loadAdapter).not.toHaveBeenCalled();
    controller.decide('granted');
    controller.start();
    expect(loadAdapter).toHaveBeenCalledTimes(1);
  });

  it('keeps analytics disabled when the manifest disables it', () => {
    const loadAdapter = vi.fn();
    const controller = createAnalyticsController({
      manifest: siteManifest,
      storage: memoryStorage(),
      loadAdapter,
    });
    controller.decide('granted');
    expect(loadAdapter).not.toHaveBeenCalled();
  });

  it('presents opt-in choices and records rejection without trackers', async () => {
    const onDecision = vi.fn();
    const manifest = { ...siteManifest, analytics: { enabled: true, provider: 'adapter' } };
    render(<ConsentBanner manifest={manifest} initialDecision="unset" onDecision={onDecision} />);
    expect(screen.getByRole('region', { name: 'Privacy choices' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Use essential only' }));
    expect(onDecision).toHaveBeenCalledWith('rejected');
  });

  it('does not prompt when no optional analytics adapter is configured', () => {
    render(<ConsentBanner manifest={siteManifest} initialDecision="unset" onDecision={vi.fn()} />);
    expect(screen.queryByRole('region', { name: 'Privacy choices' })).not.toBeInTheDocument();
  });

  it('resolves only supported locale routes with deterministic fallback', () => {
    expect(resolveLocale('de', siteManifest)).toEqual({ locale: 'de', supported: true });
    expect(resolveLocale('es', siteManifest)).toEqual({ locale: 'en', supported: false });
    expect(localizedPath('/privacy', 'de', siteManifest)).toBe('/de/privacy');
    expect(localizedPath('/privacy', 'en', siteManifest)).toBe('/privacy');
  });
});
