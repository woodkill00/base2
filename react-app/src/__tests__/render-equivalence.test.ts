import { PNG } from 'pngjs';
import { describe, expect, it } from 'vitest';
import {
  comparePngRenderEquivalence,
  RENDER_EQUIVALENCE_LIMITS,
} from '../../e2e/helpers/render-equivalence';

function bitmap(width = 100, height = 80) {
  const png = new PNG({ width, height });
  for (let offset = 0; offset < png.data.length; offset += 4) {
    png.data.set([120, 120, 120, 255], offset);
  }
  return png;
}

const encode = (png: PNG) => PNG.sync.write(png);

describe('bounded approximate PNG render equivalence', () => {
  it('keeps the reviewed limits fixed, separately from golden screenshot thresholds', () => {
    expect(RENDER_EQUIVALENCE_LIMITS).toEqual({
      maxRgbChannelDelta: 2,
      maxChangedPixelFraction: 0.00025,
    });
    expect(Object.isFrozen(RENDER_EQUIVALENCE_LIMITS)).toBe(true);
  });

  it('compares decoded RGBA rather than PNG encoding bytes', () => {
    const png = bitmap();
    const before = PNG.sync.write(png, { deflateLevel: 0, filterType: 0 });
    const after = PNG.sync.write(png, { deflateLevel: 9, filterType: 4 });
    expect(before.equals(after)).toBe(false);
    const result = comparePngRenderEquivalence(before, after);
    expect(result).toMatchObject({
      approximate: true,
      equivalent: true,
      dimensionsEqual: true,
      failures: [],
      metrics: {
        changedPixels: 0,
        changedPixelFraction: 0,
        maxRgbChannelDelta: 0,
        alphaMismatchPixels: 0,
        changedBounds: null,
      },
    });
    expect(result.before.sha256).not.toBe(result.after.sha256);
  });

  it('intentionally allows tiny RGB changes exactly at both inclusive limits', () => {
    const before = bitmap();
    const after = bitmap();
    after.data.set([122, 118, 121, 255], 0);
    after.data.set([118, 122, 119, 255], 4);
    const result = comparePngRenderEquivalence(encode(before), encode(after));
    expect(result.equivalent).toBe(true);
    expect(result.metrics).toMatchObject({
      changedPixels: 2,
      changedPixelFraction: 0.00025,
      maxRgbChannelDelta: 2,
      alphaMismatchPixels: 0,
      changedBounds: { left: 0, top: 0, right: 1, bottom: 0 },
    });
  });

  it.each([0, 1, 2])(
    'rejects one RGB channel %i delta above 2 even below the pixel budget',
    (channel) => {
      const before = bitmap();
      const after = bitmap();
      after.data[channel] += 3;
      const result = comparePngRenderEquivalence(encode(before), encode(after));
      expect(result.equivalent).toBe(false);
      expect(result.failures).toEqual(['rgb-channel-delta']);
      expect(result.metrics?.changedPixels).toBe(1);
    }
  );

  it('rejects one delta-1 pixel over the changed-pixel budget', () => {
    const before = bitmap();
    const after = bitmap();
    for (let pixel = 0; pixel < 3; pixel += 1) after.data[pixel * 4] += 1;
    const result = comparePngRenderEquivalence(encode(before), encode(after));
    expect(result.equivalent).toBe(false);
    expect(result.failures).toEqual(['changed-pixel-budget']);
    expect(result.metrics?.maxRgbChannelDelta).toBe(1);
    expect(result.metrics?.changedPixels).toBe(3);
  });

  it('does not round up a fractional one-pixel budget', () => {
    const before = bitmap(100, 39);
    const after = bitmap(100, 39);
    after.data[0] += 1;
    const result = comparePngRenderEquivalence(encode(before), encode(after));
    expect(result.equivalent).toBe(false);
    expect(result.failures).toEqual(['changed-pixel-budget']);
  });

  it.each([
    [101, 80],
    [100, 81],
    [80, 100],
  ])('rejects dimension changes to %ix%i', (width, height) => {
    const result = comparePngRenderEquivalence(encode(bitmap()), encode(bitmap(width, height)));
    expect(result.equivalent).toBe(false);
    expect(result.dimensionsEqual).toBe(false);
    expect(result.failures).toEqual(['dimensions']);
    expect(result.metrics).toBeNull();
  });

  it('requires every decoded alpha value to match exactly, even for one delta-1 pixel', () => {
    const before = bitmap();
    const after = bitmap();
    after.data[3] -= 1;
    const result = comparePngRenderEquivalence(encode(before), encode(after));
    expect(result.equivalent).toBe(false);
    expect(result.failures).toEqual(['alpha']);
    expect(result.metrics).toMatchObject({ changedPixels: 1, alphaMismatchPixels: 1 });
  });

  it.each([1, 100])(
    'rejects a one-pixel shift of a delta-%i shape without alignment or masks',
    (delta) => {
      const before = bitmap();
      const after = bitmap();
      for (let y = 10; y < 50; y += 1) {
        for (let x = 10; x < 30; x += 1) {
          before.data[(y * before.width + x) * 4] += delta;
          after.data[(y * after.width + x + 1) * 4] += delta;
        }
      }
      const result = comparePngRenderEquivalence(encode(before), encode(after));
      expect(result.equivalent).toBe(false);
      expect(result.failures).toContain('changed-pixel-budget');
      expect(result.metrics?.changedPixels).toBe(80);
    }
  );

  it('rejects visible residual controls instead of treating them as restoration noise', () => {
    const before = bitmap();
    const after = bitmap();
    for (let y = 20; y < 28; y += 1) {
      for (let x = 20; x < 44; x += 1) {
        after.data.set([125, 125, 125, 255], (y * after.width + x) * 4);
      }
    }
    const result = comparePngRenderEquivalence(encode(before), encode(after));
    expect(result.equivalent).toBe(false);
    expect(result.failures).toEqual(['rgb-channel-delta', 'changed-pixel-budget']);
    expect(result.metrics?.changedPixels).toBe(192);
  });

  it('fails closed on invalid PNG input', () => {
    expect(() => comparePngRenderEquivalence(encode(bitmap()), Buffer.from('not a PNG'))).toThrow();
  });
});
