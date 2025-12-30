import { http, HttpResponse } from 'msw';

// Basic in-memory state for tests
let currentUser = null;

export const handlers = [
  // Auth: login
  http.post('/api/auth/login', async ({ request }) => {
    const body = await request.json();
    const { email } = body || {};
    currentUser = {
      id: '1',
      email: email || 'test@example.com',
      display_name: '',
      avatar_url: '',
      bio: '',
    };
    return HttpResponse.json(currentUser, { status: 200 });
  }),

  // Auth: logout
  http.post('/api/auth/logout', () => {
    currentUser = null;
    return HttpResponse.json({}, { status: 200 });
  }),

  // Auth: me
  http.get('/api/auth/me', () => {
    if (!currentUser) {
      return HttpResponse.json({ detail: 'unauthenticated' }, { status: 401 });
    }
    return HttpResponse.json(currentUser, { status: 200 });
  }),

  // Auth: refresh
  http.post('/api/auth/refresh', () => {
    // Return a synthetic access token for axios wrapper
    return HttpResponse.json(
      { access_token: 'test_access_token', refresh_token: 'test_refresh' },
      { status: 200 }
    );
  }),

  // Flags
  http.get('/api/flags', () => {
    return HttpResponse.json({ flags: { demoMode: false } }, { status: 200 });
  }),
];
