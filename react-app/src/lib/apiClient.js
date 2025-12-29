import axios from 'axios';

// Always use relative path for API, so Traefik can route correctly
const API_URL = '/api';

let refreshPromise = null;

const _getCookie = (name) => {
  try {
    const needle = `${encodeURIComponent(name)}=`;
    const parts = String(document.cookie || '').split(';');
    for (const part of parts) {
      const trimmed = String(part || '').trim();
      if (trimmed.startsWith(needle)) {
        return decodeURIComponent(trimmed.substring(needle.length));
      }
    }
    return null;
  } catch (_) {
    return null;
  }
};

const _getAccessToken = () => {
  try {
    return window.localStorage.getItem('token');
  } catch (_) {
    return null;
  }
};

const _getRefreshToken = () => {
  try {
    return window.localStorage.getItem('refresh_token');
  } catch (_) {
    return null;
  }
};

const _setTokensFromResponse = (data) => {
  if (!data) {
    return;
  }
  try {
    if (data.access_token) {
      window.localStorage.setItem('token', data.access_token);
    }
    if (data.refresh_token) {
      window.localStorage.setItem('refresh_token', data.refresh_token);
    }
  } catch (_) {
    // ignore
  }
};

const _clearAuthStorage = () => {
  try {
    window.localStorage.removeItem('token');
    window.localStorage.removeItem('refresh_token');
    window.localStorage.removeItem('user');
  } catch (_) {
    // ignore
  }
};

const _isAuthEndpoint = (url) => {
  const path = String(url || '');
  return (
    path.includes('/auth/login') ||
    path.includes('/auth/register') ||
    path.includes('/auth/refresh') ||
    path.includes('/auth/logout') ||
    path.includes('/auth/oauth/google')
  );
};

const _refreshAccessTokenSingleFlight = async () => {
  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    const refreshToken = _getRefreshToken();
    const body = refreshToken ? { refresh_token: refreshToken } : {};

    const csrf = _getCookie('base2_csrf');
    const headers = { 'Content-Type': 'application/json' };
    if (csrf) {
      headers['X-CSRF-Token'] = csrf;
    }

    const resp = await axios.post(`${API_URL}/auth/refresh`, body, {
      withCredentials: true,
      headers,
    });

    _setTokensFromResponse(resp?.data);

    const access = resp?.data?.access_token;
    if (!access) {
      throw new Error('refresh_missing_access_token');
    }
    return access;
  })();

  try {
    return await refreshPromise;
  } finally {
    refreshPromise = null;
  }
};

const apiClient = axios.create({
  baseURL: API_URL,
  withCredentials: true,
  xsrfCookieName: 'base2_csrf',
  xsrfHeaderName: 'X-CSRF-Token',
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use(
  (config) => {
    const token = _getAccessToken();
    if (token) {
      config.headers = config.headers || {};
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error?.config;
    const status = error?.response?.status;

    if (!originalRequest || status !== 401) {
      return Promise.reject(error);
    }

    if (originalRequest.__isRetryRequest) {
      _clearAuthStorage();
      return Promise.reject(error);
    }

    if (_isAuthEndpoint(originalRequest.url)) {
      return Promise.reject(error);
    }

    originalRequest.__isRetryRequest = true;

    try {
      const newAccessToken = await _refreshAccessTokenSingleFlight();
      originalRequest.headers = originalRequest.headers || {};
      originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
      return apiClient(originalRequest);
    } catch (refreshErr) {
      _clearAuthStorage();
      return Promise.reject(refreshErr);
    }
  }
);

export default apiClient;
