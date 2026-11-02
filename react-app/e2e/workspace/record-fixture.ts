// Synthetic-only counterpart of the existing workspace journey PATCH fixture.
// Each test owns its copy; no request is forwarded to a live write endpoint.
export function createRecordFixture<
  T extends {
    id: string;
    version: number;
    title: string;
    values: Record<string, unknown>;
    publicContent: { excerpt: string; body: string };
  },
>(initial: T[]) {
  const records = structuredClone(initial);
  let updates = 0;
  return {
    list: () => structuredClone(records),
    read: (id: string) => structuredClone(records.find((record) => record.id === id)),
    get updates() {
      return updates;
    },
    patch(id: string, ifMatch: string | undefined, payload: unknown) {
      const record = records.find((item) => item.id === id);
      if (!record) return { status: 404, body: { detail: 'Record not found' } };
      if (ifMatch !== `"${record.version}"`)
        return { status: 409, body: { detail: 'Version conflict' } };
      const body = payload as {
        values?: Record<string, unknown>;
        publicContent?: { excerpt?: unknown; body?: unknown };
      } | null;
      if (
        !body ||
        !body.values ||
        typeof body.values !== 'object' ||
        Array.isArray(body.values) ||
        typeof body.values.title !== 'string' ||
        typeof body.publicContent?.excerpt !== 'string' ||
        typeof body.publicContent?.body !== 'string'
      ) {
        return { status: 422, body: { detail: 'Invalid synthetic record payload' } };
      }
      record.values = structuredClone(body.values);
      record.publicContent = structuredClone(body.publicContent) as T['publicContent'];
      record.title = body.values.title;
      record.version++;
      updates++;
      return { status: 200, body: structuredClone(record) };
    },
  };
}
