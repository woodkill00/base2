import apiClient from '../lib/apiClient';
import { normalizeApiError } from '../lib/apiErrors';

const _call = async (promise, opts) => {
  try {
    const response = await promise;
    return response.data;
  } catch (err) {
    throw normalizeApiError(err, opts);
  }
};

// Auth API calls
export const authAPI = {
  // Register new user (cookie session)
  register: async (email, password, _name) => {
    return _call(apiClient.post('/auth/register', { email, password }), {
      fallbackMessage: 'Registration failed',
    });
  },

  // Login with email/password (cookie session)
  login: async (email, password) => {
    return _call(apiClient.post('/auth/login', { email, password }), {
      fallbackMessage: 'Login failed',
    });
  },

  // Logout (cookie session)
  logout: async () => {
    return _call(apiClient.post('/auth/logout'), { fallbackMessage: 'Logout failed' });
  },

  // Get current user (cookie session)
  getMe: async () => {
    return _call(apiClient.get('/auth/me'), { fallbackMessage: 'Failed to load user' });
  },

  // Google OAuth login
  googleAuth: async (credential) => {
    return _call(apiClient.post('/auth/oauth/google', { credential }), {
      fallbackMessage: 'Google login failed',
    });
  },

  // Verify email
  verifyEmail: async (token) => {
    return _call(apiClient.post('/auth/verify-email', { token }), {
      fallbackMessage: 'Email verification failed',
    });
  },

  // Resend verification email
  resendVerification: async (email) => {
    return _call(apiClient.post('/auth/resend-verification', { email }), {
      fallbackMessage: 'Failed to resend verification email',
    });
  },

  // Request password reset
  forgotPassword: async (email) => {
    return _call(apiClient.post('/auth/forgot-password', { email }), {
      fallbackMessage: 'Failed to send reset email',
    });
  },

  // Reset password
  resetPassword: async (token, password) => {
    return _call(apiClient.post('/auth/reset-password', { token, password }), {
      fallbackMessage: 'Password reset failed',
    });
  },

  // List active sessions (refresh tokens)
  listSessions: async () => {
    return _call(apiClient.get('/auth/sessions'), {
      fallbackMessage: 'Failed to load sessions',
    });
  },

  // Revoke all sessions except the current one
  revokeOtherSessions: async () => {
    return _call(apiClient.post('/auth/sessions/revoke-others'), {
      fallbackMessage: 'Failed to log out other devices',
    });
  },

};

export default apiClient;
