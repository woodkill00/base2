// Versioned CSS-space geometry used by capture and reference schedule checks.
// Python independently recomputes these quantities when accepting transport.
export const GEOMETRY_VERSION = 1;
export const GEOMETRY_TOLERANCE = 1;
export type Geometry = {
  offset: number;
  max: number;
  height: number;
  inset: number;
  scale: number;
  viewport: number[];
  rect: number[];
};
export function deriveGeometry(g: Geometry) {
  const [x, y, width, rectHeight] = g.rect;
  const [vw, vh, dpr] = g.viewport;
  const { offset, max, height, inset, scale } = g;
  if (
    ![x, y, width, rectHeight, vw, vh, dpr, offset, max, height, inset, scale].every(
      Number.isFinite
    ) ||
    scale <= 0 ||
    dpr <= 0 ||
    height <= 0 ||
    width <= 0 ||
    rectHeight <= 0 ||
    max < 0 ||
    offset < 0 ||
    offset > max + 1 ||
    inset < 0 ||
    inset >= height ||
    x < -1 ||
    x + width > vw + 1 ||
    y >= vh ||
    y + rectHeight <= 0 ||
    rectHeight / scale - height < -1 ||
    rectHeight / scale - height > 2
  )
    throw new Error('invalid sequence geometry');
  const extent = max + height - inset;
  const start = offset + Math.max(inset, (Math.max(y, 0) - y) / scale) - inset;
  const end = Math.min(max + height, offset + (Math.min(y + rectHeight, vh) - y) / scale) - inset;
  if (start < 0 || end <= start || end > extent + 1) throw new Error('invalid visible interval');
  return { extent, start, end, next: Math.min(max, offset + (end - start) * 0.75) };
}
export function scheduleRow(g: Geometry) {
  return {
    offset: g.offset,
    max: g.max,
    height: g.height,
    inset: g.inset,
    scale: g.scale,
    viewport: g.viewport,
    rect: g.rect,
    ...deriveGeometry(g),
  };
}
