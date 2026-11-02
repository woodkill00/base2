import { expect, test } from 'vitest';
import { coverageErrors, type Segment } from '../../e2e/continuous-coverage';
const frame = (index: number, start: number, end: number): Segment => ({
  index,
  start,
  end,
  extent: 1000,
  route: '/media',
  offset: start,
});
const valid = [frame(0, 0, 400), frame(1, 300, 700), frame(2, 600, 1000)];
test('overlapping native intervals cover complete extent', () =>
  expect(coverageErrors(valid, '/media', 1000)).toEqual([]));
test.each([
  ['gap', [frame(0, 0, 400), frame(1, 450, 1000)]],
  ['nonprogress', [valid[0], { ...valid[0], index: 1 }, ...valid.slice(1)]],
  ['index', [valid[0], { ...valid[1], index: 0 }, valid[2]]],
  ['route', [valid[0], { ...valid[1], route: '/other' }, valid[2]]],
  ['extent', [valid[0], { ...valid[1], extent: 1200 }, valid[2]]],
  ['geometry', [valid[0], { ...valid[1], end: NaN }, valid[2]]],
  ['incomplete', valid.slice(0, 2)],
  ['empty', []],
])('rejects %s instead of declaring complete evidence', (error, segments) => {
  expect(coverageErrors(segments as Segment[], '/media', 1000)).toContain(error);
});
test('segment ceiling never implies coverage', () =>
  expect(coverageErrors(valid, '/media', 1000, 2)).toContain('limit'));

test('touching intervals are insufficient: independently reviewable frames must overlap', () => {
  expect(
    coverageErrors([frame(0, 0, 400), frame(1, 400, 800), frame(2, 700, 1000)], '/media', 1000)
  ).toContain('overlap');
});
