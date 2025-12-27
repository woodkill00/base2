import React, { createContext, useContext, useState, useEffect } from 'react';
import { authAPI } from '../services/api';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    const storedUser = localStorage.getItem('user');
    if (!storedUser) {
      return null;
    }

    try {
      return JSON.parse(storedUser);
    } catch (error) {
      console.error('Error parsing stored user:', error);
      localStorage.removeItem('user');
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
        localStorage.setItem('user', JSON.stringify(userPayload));
        if (userPayload.access_token) {
          localStorage.setItem('token', userPayload.access_token);
        }
      }
      return { success: true, data: userPayload };
    } catch (error) {
      const message = error.response?.data?.detail || error.response?.data?.message || 'Registration failed';
      setError(message);
      return { success: false, error: message };
    }
  };

  // Login with email/password
  const loginWithEmail = async (email, password) => {
    try {
      setError(null);
      const userPayload = await authAPI.login(email, password);

      if (userPayload && userPayload.email) {
        localStorage.setItem('user', JSON.stringify(userPayload));
        if (userPayload.access_token) {
          localStorage.setItem('token', userPayload.access_token);
        }
        setUser(userPayload);
        return { success: true };
      }

      return { success: false, error: 'Invalid response from server' };
    } catch (error) {
      const message = error.response?.data?.detail || error.response?.data?.message || 'Login failed';
      setError(message);
      return { success: false, error: message };
    }
  };

  // Login with Google OAuth
  const loginWithGoogle = async (googleId, email, name, picture) => {
    try {
      setError(null);
      const data = await authAPI.googleAuth(googleId, email, name, picture);
      
      if (data.success && data.token) {
        localStorage.setItem('token', data.token);
        localStorage.setItem('user', JSON.stringify(data.user));
        setUser(data.user);
        return { success: true };
      }
      
      return { success: false, error: 'Invalid response from server' };
    } catch (error) {
      const message = error.response?.data?.message || 'Google login failed';
      setError(message);
      return { success: false, error: message };
    }
  };

  // Legacy login function for compatibility
  const login = (userData, token = null) => {
    setUser(userData);
    localStorage.setItem('user', JSON.stringify(userData));
    if (token) {
      localStorage.setItem('token', token);
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
      localStorage.removeItem('user');
      localStorage.removeItem('token');
    }
  };

  // Update user profile
  const updateUser = (userData) => {
    const updatedUser = { ...(user || {}), ...userData };
    setUser(updatedUser);
    localStorage.setItem('user', JSON.stringify(updatedUser));
  };

  // Verify email
  const verifyEmail = async (token) => {
    try {
      setError(null);
      const data = await authAPI.verifyEmail(token);
      const message = data?.detail || 'Email verified successfully!';
      return { success: true, message };
    } catch (error) {
      const message = error.response?.data?.detail || 'Email verification failed';
      setError(message);
      return { success: false, error: message };
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
      const message = error.response?.data?.detail || 'Failed to send reset email';
      setError(message);
      return { success: false, error: message };
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
      const message = error.response?.data?.detail || 'Password reset failed';
      setError(message);
      return { success: false, error: message };
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
