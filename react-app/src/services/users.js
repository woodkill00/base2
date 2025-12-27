import api from './api';

// Legacy compatibility wrapper; Option A auth endpoints are /auth/*.
export const usersAPI = {
  me: async () => {
    const res = await api.get('/auth/me');
    return res.data;
  },
  login: async (email, password) => {
    const res = await api.post('/auth/login', { email, password });
    return res.data;
  },
  logout: async () => {
    const res = await api.post('/auth/logout');
    return res.data;
  },
};
