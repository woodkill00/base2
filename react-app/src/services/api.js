import apiClient from '../lib/apiClient';

// Auth API calls
export const authAPI = {
  // Register new user (cookie session)
  register: async (email, password, _name) => {
    const response = await apiClient.post('/auth/register', { email, password });
    return response.data;
  },

  // Login with email/password (cookie session)
  login: async (email, password) => {
    const response = await apiClient.post('/auth/login', { email, password });
    return response.data;
  },

  // Logout (cookie session)
  logout: async () => {
    const response = await apiClient.post('/auth/logout');
    return response.data;
  },

  // Get current user (cookie session)
  getMe: async () => {
    const response = await apiClient.get('/auth/me');
    return response.data;
  },

  // Google OAuth login
  googleAuth: async (credential) => {
    const response = await apiClient.post('/auth/oauth/google', { credential });
    return response.data;
  },

  // Verify email
  verifyEmail: async (token) => {
    const response = await apiClient.post('/auth/verify-email', { token });
    return response.data;
  },

  // Resend verification email
  resendVerification: async (email) => {
    const response = await apiClient.post('/auth/resend-verification', { email });
    return response.data;
  },

  // Request password reset
  forgotPassword: async (email) => {
    const response = await apiClient.post('/auth/forgot-password', { email });
    return response.data;
  },

  // Reset password
  resetPassword: async (token, password) => {
    const response = await apiClient.post('/auth/reset-password', { token, password });
    return response.data;
  },

};

export default apiClient;
