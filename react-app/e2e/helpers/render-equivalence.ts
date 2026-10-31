import { createHash } from 'node:crypto';
import { PNG } from 'pngjs';

export const RENDER_EQUIVALENCE_LIMITS = Object.freeze({
  maxRgbChannelDelta: 2,
  maxChangedPixelFraction: 0.00025,
});

/**
 * Bounded, approximate restoration check, NOT perceptual or exact pixel equality.
 * Tiny changes inside BOTH RGB limits are intentionally allowed. Dimensions and
 * every decoded alpha value must match exactly. No resizing, alignment, masks,
 * gamma correction or anti-alias exclusion is applied, including transparent RGB.
 * This does not replace or change the independent golden screenshot assertion.
 */
export function comparePngRenderEquivalence(beforeBytes: Buffer, afterBytes: Buffer) {
  const before = PNG.sync.read(beforeBytes, { checkCRC: true });
  const after = PNG.sync.read(afterBytes, { checkCRC: true });
  const describe = (png: PNG, bytes: Buffer) => ({
    width: png.width,
    height: png.height,
    encodedBytes: bytes.length,
    sha256: createHash('sha256').update(bytes).digest('hex'),
  });
  const dimensionsEqual = before.width === after.width && before.height === after.height;
  const failures: string[] = [];
  let metrics = null;

  if (!dimensionsEqual) {
    failures.push('dimensions');
  } else {
    const totalPixels = before.width * before.height;
    let changedPixels = 0;
    let maxRgbChannelDelta = 0;
    let alphaMismatchPixels = 0;
    let left = before.width;
    let top = before.height;
    let right = -1;
    let bottom = -1;
    for (let pixel = 0; pixel < totalPixels; pixel += 1) {
      const offset = pixel * 4;
      const rgbDelta = Math.max(
        Math.abs(before.data[offset] - after.data[offset]),
        Math.abs(before.data[offset + 1] - after.data[offset + 1]),
        Math.abs(before.data[offset + 2] - after.data[offset + 2])
      );
      const alphaChanged = before.data[offset + 3] !== after.data[offset + 3];
      maxRgbChannelDelta = Math.max(maxRgbChannelDelta, rgbDelta);
      if (alphaChanged) alphaMismatchPixels += 1;
      if (rgbDelta > 0 || alphaChanged) {
        changedPixels += 1;
        const x = pixel % before.width;
        const y = Math.floor(pixel / before.width);
        left = Math.min(left, x);
        top = Math.min(top, y);
        right = Math.max(right, x);
        bottom = Math.max(bottom, y);
      }
    }
    const changedPixelFraction = changedPixels / totalPixels;
    metrics = {
      totalPixels,
      changedPixels,
      changedPixelFraction,
      maxRgbChannelDelta,
      alphaMismatchPixels,
      changedBounds: changedPixels ? { left, top, right, bottom } : null,
    };
    if (alphaMismatchPixels > 0) failures.push('alpha');
    if (maxRgbChannelDelta > RENDER_EQUIVALENCE_LIMITS.maxRgbChannelDelta) {
      failures.push('rgb-channel-delta');
    }
    if (changedPixelFraction > RENDER_EQUIVALENCE_LIMITS.maxChangedPixelFraction) {
      failures.push('changed-pixel-budget');
    }
  }

  return {
    approximate: true,
    equivalent: failures.length === 0,
    limits: RENDER_EQUIVALENCE_LIMITS,
    before: describe(before, beforeBytes),
    after: describe(after, afterBytes),
    dimensionsEqual,
    metrics,
    failures,
  };
}
