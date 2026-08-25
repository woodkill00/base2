import apiClient from '../lib/apiClient';
import { siteManifest } from '../config/siteRuntime';
const headers = { 'X-Tenant-Id': siteManifest.siteId };
export const schedulingAPI = {
  list: async () => (await apiClient.get('/scheduling/events', { headers })).data,
  reserve: async (eventId, seats = 1) =>
    (
      await apiClient.post(
        `/scheduling/events/${encodeURIComponent(eventId)}/bookings`,
        { seats },
        { headers }
      )
    ).data,
};
