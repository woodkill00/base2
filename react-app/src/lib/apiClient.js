import axios from 'axios';
import { siteManifest } from '../config/siteRuntime';
import { authSession } from './authSession';

// Always use relative path for API, so Traefik can route correctly
const API_URL = '/api';

let refreshPromise = null;

export const withSessionLock = (operation) =>
  navigator.locks?.request
    ? navigator.locks.request(
        'base2-auth-session',
        { signal: AbortSignal.timeout(15000) },
        operation
      )
    : Promise.resolve().then(operation);

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

const _detectCookieNameBySuffix = (suffix) => {
  try {
    const parts = String(document.cookie || '').split(';');
    for (const part of parts) {
      const trimmed = String(part || '').trim();
      if (!trimmed) continue;
      const eq = trimmed.indexOf('=');
      if (eq <= 0) continue;
      const name = decodeURIComponent(trimmed.slice(0, eq));
      if (name && name.endsWith(suffix)) {
        return name;
      }
    }
    return null;
  } catch (_) {
    return null;
  }
};

const _getCsrfToken = () => {
  const name = _detectCookieNameBySuffix('_csrf');
  return name ? _getCookie(name) : null;
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

export const restoreSession = async () => {
  if (refreshPromise) {
    return refreshPromise;
  }

  const epoch = authSession.epoch();
  const refresh = async () => {
    if (!authSession.canRestore() || epoch !== authSession.epoch()) {
      throw new Error('Session restoration blocked');
    }
    const csrf = _getCsrfToken();
    const headers = { 'Content-Type': 'application/json', 'X-Tenant-Id': siteManifest.siteId };
    if (csrf) {
      headers['X-CSRF-Token'] = csrf;
    }

    const resp = await axios.post(
      `${API_URL}/auth/refresh`,
      {},
      {
        withCredentials: true,
        headers,
        timeout: 10000,
      }
    );
    const profile = authSession.accept(resp?.data, epoch);
    if (!profile) {
      throw new Error('Session changed during restoration');
    }
    return profile;
  };
  // Serialize rotating HttpOnly cookies across tabs without sharing credentials.
  // Unsupported browsers must explicitly sign in rather than race rotations.
  if (!navigator.locks?.request) throw new Error('Secure session restoration unavailable');
  refreshPromise = withSessionLock(refresh);

  try {
    return await refreshPromise;
  } finally {
    refreshPromise = null;
  }
};

const apiClient = axios.create({
  baseURL: API_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use(
  (config) => {
    if (String(config.url || '').startsWith('/auth/') && config.timeout === 0)
      config.timeout = 10000;
    config.headers = config.headers || {};
    config.headers['X-Tenant-Id'] = siteManifest.siteId;
    const csrf = _getCsrfToken();
    if (csrf) {
      config.headers['X-CSRF-Token'] = csrf;
    }
    config.__authEpoch = authSession.epoch();
    const token = authSession.access();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

apiClient.interceptors.response.use(
  (response) => {
    if (
      response.config?.__authEpoch !== undefined &&
      response.config.__authEpoch !== authSession.epoch()
    ) {
      return Promise.reject(new Error('Session changed during request'));
    }
    return response;
  },
  async (error) => {
    const originalRequest = error?.config;
    const status = error?.response?.status;

    if (!originalRequest || status !== 401) {
      return Promise.reject(error);
    }

    if (originalRequest.__authEpoch !== authSession.epoch()) return Promise.reject(error);

    // Freshness is not expiry. Never refresh/replay a sensitive mutation or
    // discard a valid session when the server requires explicit authentication.
    if (error?.response?.data?.detail === 'recent_reauthentication_required') {
      authSession.requireReauthentication();
      return Promise.reject(error);
    }
    if (originalRequest.__isRetryRequest) {
      authSession.invalidate('expired');
      return Promise.reject(error);
    }

    if (_isAuthEndpoint(originalRequest.url)) {
      return Promise.reject(error);
    }

    originalRequest.__isRetryRequest = true;

    try {
      await restoreSession();
      if (originalRequest.__authEpoch !== authSession.epoch()) throw new Error('Session changed');
      const newAccessToken = authSession.access();
      originalRequest.headers = originalRequest.headers || {};
      originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
      return apiClient(originalRequest);
    } catch (refreshErr) {
      if (originalRequest.__authEpoch === authSession.epoch()) authSession.invalidate('expired');
      return Promise.reject(refreshErr);
    }
  }
);

export default apiClient;
