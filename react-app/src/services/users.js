import api from './api';

export const usersAPI = {
  list: async () => {
    const res = await api.get('/users');
    return res.data;
  },
  me: async () => {
    const res = await api.get('/users/me');
    return res.data;
  },
  login: async (email, password) => {
    const res = await api.post('/users/login', { email, password });
    return res.data;
  },
  logout: async () => {
    const res = await api.post('/users/logout');
    return res.data;
  },
};
