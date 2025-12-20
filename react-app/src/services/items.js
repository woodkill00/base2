import api from './api';

export const itemsAPI = {
  list: async () => {
    const res = await api.get('/items');
    return res.data.items || [];
  },
  create: async (name, description='') => {
    const res = await api.post('/items', { name, description });
    return res.data.item;
  },
  get: async (id) => {
    const res = await api.get(`/items/${id}`);
    return res.data.item;
  }
};
