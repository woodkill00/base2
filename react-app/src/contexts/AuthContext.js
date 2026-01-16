import { createContext, useContext, useEffect, useState } from 'react';
import { authAPI } from '../services/api';
import { normalizeApiError } from '../lib/apiErrors';

const AuthContext = createContext(null);

const safeStorageGet = (key) => {
  try {
    return window.localStorage.getItem(key);
  } catch (_) {
    return null;
  }
};

const safeStorageSet = (key, value) => {
  try {
    window.localStorage.setItem(key, value);
  } catch (_) {
    // ignore
  }
};

const safeStorageRemove = (key) => {
  try {
    window.localStorage.removeItem(key);
  } catch (_) {
    // ignore
  }
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    const storedUser = safeStorageGet('user');
    if (!storedUser) {
      return null;
    }

    try {
      return JSON.parse(storedUser);
    } catch (error) {
      safeStorageRemove('user');
      return null;
    }
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    // If we ever add async session verification, this is the hook.
    setLoading(false);
  }, []);

  // Register with email/password
  const register = async (email, password, name) => {
    try {
      setError(null);
      const userPayload = await authAPI.register(email, password, name);
      if (userPayload && userPayload.email) {
        setUser(userPayload);
        safeStorageSet('user', JSON.stringify(userPayload));
        if (userPayload.access_token) {
          safeStorageSet('token', userPayload.access_token);
        }
        if (userPayload.refresh_token) {
          safeStorageSet('refresh_token', userPayload.refresh_token);
        }
      }
      return { success: true, data: userPayload };
    } catch (error) {
      const apiErr = normalizeApiError(error, { fallbackMessage: 'Registration failed' });
      setError(apiErr.message);
      return { success: false, error: apiErr.message, fields: apiErr.fields || null, code: apiErr.code };
    }
  };

  // Login with email/password
  const loginWithEmail = async (email, password) => {
    try {
      setError(null);
      const userPayload = await authAPI.login(email, password);

      if (userPayload && userPayload.email) {
        safeStorageSet('user', JSON.stringify(userPayload));
        if (userPayload.access_token) {
          safeStorageSet('token', userPayload.access_token);
        }
        if (userPayload.refresh_token) {
          safeStorageSet('refresh_token', userPayload.refresh_token);
        }
        setUser(userPayload);
        return { success: true };
      }

      return { success: false, error: 'Invalid response from server' };
    } catch (error) {
      const apiErr = normalizeApiError(error, { fallbackMessage: 'Login failed' });
      setError(apiErr.message);
      return { success: false, error: apiErr.message, fields: apiErr.fields || null, code: apiErr.code };
    }
  };

  // Login with Google OAuth
  const loginWithGoogle = async (credential) => {
    try {
      setError(null);
      const data = await authAPI.googleAuth(credential);

      if (data && data.email && data.access_token) {
        safeStorageSet('token', data.access_token);
        if (data.refresh_token) {
          safeStorageSet('refresh_token', data.refresh_token);
        }
        safeStorageSet('user', JSON.stringify(data));
        setUser(data);
        return { success: true };
      }

      return { success: false, error: 'Invalid response from server' };
    } catch (error) {
      const apiErr = normalizeApiError(error, { fallbackMessage: 'Google login failed' });
      setError(apiErr.message);
      return { success: false, error: apiErr.message, fields: apiErr.fields || null, code: apiErr.code };
    }
  };

  // Legacy login function for compatibility
  const login = (userData, token = null) => {
    setUser(userData);
    safeStorageSet('user', JSON.stringify(userData));
    if (token) {
      safeStorageSet('token', token);
    }
  };

  // Logout
  const logout = async () => {
    try {
      await authAPI.logout();
    } catch (error) {
      // Ignore network/server errors; we still clear local session state.
    } finally {
      setUser(null);
      safeStorageRemove('user');
      safeStorageRemove('token');
      safeStorageRemove('refresh_token');
    }
  };

  // Update user profile
  const updateUser = (userData) => {
    const updatedUser = { ...(user || {}), ...userData };
    setUser(updatedUser);
    safeStorageSet('user', JSON.stringify(updatedUser));
  };

  // Verify email
  const verifyEmail = async (token) => {
    try {
      setError(null);
      const data = await authAPI.verifyEmail(token);
      const message = data?.detail || 'Email verified successfully!';
      return { success: true, message };
    } catch (error) {
      const apiErr = normalizeApiError(error, { fallbackMessage: 'Email verification failed' });
      setError(apiErr.message);
      return { success: false, error: apiErr.message, fields: apiErr.fields || null, code: apiErr.code };
    }
  };

  // Request password reset
  const forgotPassword = async (email) => {
    try {
      setError(null);
      const data = await authAPI.forgotPassword(email);
      const message = data?.detail || 'If the account exists, a password reset email has been sent';
      return { success: true, message };
    } catch (error) {
      const apiErr = normalizeApiError(error, { fallbackMessage: 'Failed to send reset email' });
      setError(apiErr.message);
      return { success: false, error: apiErr.message, fields: apiErr.fields || null, code: apiErr.code };
    }
  };

  // Reset password
  const resetPassword = async (token, password) => {
    try {
      setError(null);
      const data = await authAPI.resetPassword(token, password);
      const message = data?.detail || 'Password reset successfully';
      return { success: true, message };
    } catch (error) {
      const apiErr = normalizeApiError(error, { fallbackMessage: 'Password reset failed' });
      setError(apiErr.message);
      return { success: false, error: apiErr.message, fields: apiErr.fields || null, code: apiErr.code };
    }
  };

  const value = {
    user,
    loading,
    error,
    isAuthenticated: !!user,
    register,
    loginWithEmail,
    loginWithGoogle,
    login, // Keep for compatibility
    logout,
    updateUser,
    verifyEmail,
    forgotPassword,
    resetPassword,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
