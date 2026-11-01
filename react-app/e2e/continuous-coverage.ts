// Pure checks shared by the native collector and deterministic unit regressions.
export type Segment = {
  index: number;
  route: string;
  start: number;
  end: number;
  extent: number;
  offset: number;
};
export function coverageErrors(segments: Segment[], route: string, extent: number, limit = 64) {
  const errors = new Set<string>();
  if (!segments.length) errors.add('empty');
  if (segments.length > limit) errors.add('limit');
  let previousHeight = 0;
  let end = 0,
    offset = -1;
  segments.forEach((s, i) => {
    if (s.index !== i) errors.add('index');
    if (s.route !== route) errors.add('route');
    if (s.extent !== extent) errors.add('extent');
    if (
      ![s.start, s.end, s.offset, s.extent].every(Number.isFinite) ||
      s.start < 0 ||
      s.end <= s.start ||
      s.end > extent + 1
    )
      errors.add('geometry');
    if (s.start > end + 1) errors.add('gap');
    if (i && s.start > end - previousHeight * 0.25 + 1) errors.add('overlap');
    if (i && (s.offset <= offset || s.end <= end)) errors.add('nonprogress');
    previousHeight = s.end - s.start;
    offset = s.offset;
    end = Math.max(end, s.end);
  });
  if (end < extent - 1) errors.add('incomplete');
  return [...errors];
}
