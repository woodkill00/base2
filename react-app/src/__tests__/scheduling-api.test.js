import { beforeEach, expect, it, vi } from 'vitest';
import apiClient from '../lib/apiClient';
import { schedulingAPI } from '../services/scheduling';
vi.mock('../lib/apiClient', () => ({ default: { get: vi.fn(), post: vi.fn() } }));
beforeEach(() => vi.clearAllMocks());
it('binds event reads and booking writes to the generated tenant', async () => {
  apiClient.get.mockResolvedValue({ data: { items: [] } });
  apiClient.post.mockResolvedValue({ data: { status: 'confirmed' } });
  await schedulingAPI.list();
  await schedulingAPI.reserve('event one', 2);
  expect(apiClient.get).toHaveBeenCalledWith('/scheduling/events', {
    headers: { 'X-Tenant-Id': 'ember-studio' },
  });
  expect(apiClient.post).toHaveBeenCalledWith(
    '/scheduling/events/event%20one/bookings',
    { seats: 2 },
    { headers: { 'X-Tenant-Id': 'ember-studio' } }
  );
});
