import { useEffect, useState } from 'react';

import apiClient from '../lib/apiClient';

export const useAuth = () => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      try {
        setUser(JSON.parse(storedUser));
      } catch (_) {
        localStorage.removeItem('user');
      } finally {
        setLoading(false);
      }
      return;
    }

    (async () => {
      try {
        const resp = await apiClient.get('/users/me');
        if (resp?.data) {
          setUser(resp.data);
          localStorage.setItem('user', JSON.stringify(resp.data));
        }
      } catch (err) {
        // Treat unauth and network errors as unauthenticated.
        setError(err);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return {
    user,
    loading,
    authenticated: !!user,
    error,
  };
};
