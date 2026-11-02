import { expect, test } from 'vitest';
import { createRecordFixture } from '../../e2e/workspace/record-fixture';

const original = {
  id: 'synthetic-record',
  version: 1,
  title: 'Original',
  values: { title: 'Original', note: 'Private fixture' },
  publicContent: { excerpt: 'Public excerpt', body: 'Public body' },
};
test('synthetic PATCH persists only explicit values/public content and rejects stale or absent versions', () => {
  const fixture = createRecordFixture([original]);
  const payload = {
    values: { title: 'Edited', note: 'Private fixture' },
    publicContent: { excerpt: 'Edited excerpt', body: 'Edited body' },
  };
  expect(fixture.patch(original.id, '"1"', payload)).toMatchObject({
    status: 200,
    body: { title: 'Edited', version: 2, ...payload },
  });
  expect(fixture.read(original.id)).toMatchObject({ title: 'Edited', version: 2, ...payload });
  expect(fixture.list()[0]).toEqual(fixture.read(original.id));
  for (const version of ['"1"', undefined, '2'])
    expect(fixture.patch(original.id, version, payload).status).toBe(409);
  expect(fixture.updates).toBe(1);
  expect(original.version).toBe(1);
  expect(createRecordFixture([original]).read(original.id)).toEqual(original);
});
test('reading/discarding an independent draft never mutates the synthetic server; malformed writes fail', () => {
  const fixture = createRecordFixture([original]);
  const draft = fixture.read(original.id)!;
  draft.values.title = 'Discarded';
  expect(fixture.read(original.id)).toEqual(original);
  expect(fixture.updates).toBe(0);
  expect(fixture.patch(original.id, '"1"', null).status).toBe(422);
  expect(fixture.patch('absent', '"1"', original).status).toBe(404);
});
