import apiClient from '../lib/apiClient';
import { normalizeOperationsError, operationsAPI } from '../services/operations';

vi.mock('../lib/apiClient', () => ({
  default: { get: vi.fn(), post: vi.fn() },
}));

vi.mock('../lib/apiErrors', () => ({
  normalizeApiError: vi.fn((_error, options) => options),
}));

beforeEach(() => vi.clearAllMocks());

test('loads summary and bounded incidents while unwrapping the API envelope', async () => {
  const signal = new AbortController().signal;
  apiClient.get
    .mockResolvedValueOnce({ data: { data: { services: { total: 2 } } } })
    .mockResolvedValueOnce({ data: { incidents: [] } });
  await expect(operationsAPI.summary({ signal })).resolves.toEqual({ services: { total: 2 } });
  await expect(operationsAPI.incidents({ limit: 17, signal })).resolves.toEqual({ incidents: [] });
  expect(apiClient.get).toHaveBeenNthCalledWith(1, '/operations/v1/summary', { signal });
  expect(apiClient.get).toHaveBeenNthCalledWith(2, '/operations/v1/incidents', {
    params: { limit: 17 },
    signal,
  });
});

test('encodes incident identity for acknowledgement and normalizes failures', async () => {
  apiClient.post.mockResolvedValue({ data: { data: { status: 'acknowledged' } } });
  await expect(operationsAPI.acknowledge('incident/one')).resolves.toEqual({
    status: 'acknowledged',
  });
  expect(apiClient.post).toHaveBeenCalledWith(
    '/operations/v1/incidents/incident%2Fone/acknowledge'
  );
  expect(normalizeOperationsError(new Error('private detail'))).toEqual({
    fallbackMessage: 'Operations information is temporarily unavailable.',
  });
});
