import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { authAPI } from '../services/api';
import { normalizeApiError } from '../lib/apiErrors';
import { authSession } from '../lib/authSession';
import { restoreSession, withSessionLock } from '../lib/apiClient';
import { ReauthenticationNoticeContext } from './ReauthenticationNoticeContext';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sessionNotice, setSessionNotice] = useState(null);
  const [reauthenticationRequired, setReauthenticationRequired] = useState(false);
  const busy = useRef(false);
  const mounted = useRef(false);

  useEffect(() => {
    mounted.current = true;
    let active = true;
    authSession.initialize();
    const epoch = authSession.epoch();
    const unsubscribe = authSession.subscribe((reason) => {
      if (reason === 'reauthentication-required') {
        setReauthenticationRequired(true);
        return;
      }
      setReauthenticationRequired(false);
      setUser(null);
      setSessionNotice(reason === 'expired' ? 'Your session ended. Please sign in again.' : null);
    });
    const onStorage = (event) => authSession.storageChanged(event);
    const onPageShow = () => {
      if (authSession.access() && !authSession.canRestore()) authSession.invalidate();
    };
    window.addEventListener('storage', onStorage);
    window.addEventListener('pageshow', onPageShow);
    // StrictMode shares the client's single-flight request; discarded effects
    // cannot apply its result or clear another effect's verified session.
    const bootstrap = async () => {
      try {
        if (authSession.canRestore()) {
          const profile = await restoreSession();
          if (active && epoch === authSession.epoch()) setUser(profile);
        }
      } catch (cause) {
        // Missing cookies are normal for signed-out visitors. Never trust a
        // persisted profile or infer authentication from a failed refresh.
        if (active) {
          setUser(null);
          if (cause?.response?.status !== 401)
            setSessionNotice('Your previous sign-in could not be restored. Please sign in again.');
        }
      } finally {
        if (active) setLoading(false);
      }
    };
    bootstrap();
    return () => {
      active = false;
      mounted.current = false;
      unsubscribe();
      window.removeEventListener('storage', onStorage);
      window.removeEventListener('pageshow', onPageShow);
    };
  }, []);

  const authenticate = async (operation, fallbackMessage) => {
    if (loading || busy.current)
      return { success: false, error: 'Please wait for the current sign-in request.' };
    busy.current = true;
    const epoch = authSession.epoch();
    try {
      setError(null);
      const payload = await withSessionLock(async () => {
        if (!mounted.current || epoch !== authSession.epoch())
          throw new Error('Sign-in was cancelled.');
        return operation();
      });
      if (!mounted.current || epoch !== authSession.epoch())
        return { success: false, error: 'Sign-in was cancelled.' };
      if (payload?.mfa_required && payload?.challenge_token) {
        return {
          success: false,
          mfaRequired: true,
          challengeToken: payload.challenge_token,
          methods: payload.methods || [],
          expiresIn: payload.expires_in,
        };
      }
      const profile = authSession.accept(payload, epoch, { explicit: true });
      if (!profile) return { success: false, error: 'Sign-in was cancelled.' };
      setUser(profile);
      setSessionNotice(null);
      setReauthenticationRequired(false);
      return { success: true, data: profile };
    } catch (cause) {
      const apiErr = normalizeApiError(cause, { fallbackMessage });
      if (mounted.current && epoch === authSession.epoch()) setError(apiErr.message);
      return {
        success: false,
        error: apiErr.message,
        fields: apiErr.fields || null,
        code: apiErr.code,
      };
    } finally {
      busy.current = false;
    }
  };

  const register = (email, password, name) =>
    authenticate(() => authAPI.register(email, password, name), 'Registration failed');
  const loginWithEmail = (email, password) =>
    authenticate(() => authAPI.login(email, password), 'Login failed');
  const loginWithGoogle = (credential) =>
    authenticate(() => authAPI.googleAuth(credential), 'Google login failed');
  const completeMfaLogin = (challengeToken, code) =>
    authenticate(
      () => authAPI.completeMfaLogin(challengeToken, code),
      'Authentication code was not accepted'
    );

  // Compatibility requires an actual token, never an arbitrary persisted user.
  const login = (userData, token = null) => {
    const profile = authSession.accept({ ...userData, access_token: token }, authSession.epoch(), {
      explicit: true,
    });
    setUser(profile);
    setReauthenticationRequired(false);
  };

  const logout = async () => {
    authSession.invalidate();
    setUser(null);
    try {
      await withSessionLock(() => authAPI.logout());
      setSessionNotice('You are signed out.');
      return { success: true, serverConfirmed: true };
    } catch (_) {
      const message =
        'Signed out on this browser, but server logout could not be confirmed. Please retry logout when your connection returns.';
      setSessionNotice(message);
      return { success: false, serverConfirmed: false, error: message };
    }
  };

  const updateUser = (data) =>
    setUser((current) => (current ? { ...current, ...authSession.profile(data) } : null));

  const accountAction = useCallback(async (operation, fallbackMessage, successMessage) => {
    try {
      setError(null);
      const data = await operation();
      return { success: true, message: data?.detail || successMessage };
    } catch (cause) {
      const apiErr = normalizeApiError(cause, { fallbackMessage });
      setError(apiErr.message);
      return {
        success: false,
        error: apiErr.message,
        fields: apiErr.fields || null,
        code: apiErr.code,
      };
    }
  }, []);
  const verifyEmail = useCallback(
    (token) =>
      accountAction(
        () => authAPI.verifyEmail(token),
        'Email verification failed',
        'Email verified successfully!'
      ),
    [accountAction]
  );
  const forgotPassword = (email) =>
    accountAction(
      () => authAPI.forgotPassword(email),
      'Failed to send reset email',
      'If the account exists, a password reset email has been requested'
    );
  const resetPassword = (token, password) =>
    accountAction(
      () => authAPI.resetPassword(token, password),
      'Password reset failed',
      'Password reset successfully'
    );

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        error,
        sessionNotice,
        reauthenticationRequired,
        isAuthenticated: !!user,
        register,
        loginWithEmail,
        completeMfaLogin,
        loginWithGoogle,
        login,
        logout,
        updateUser,
        verifyEmail,
        forgotPassword,
        resetPassword,
      }}
    >
      <ReauthenticationNoticeContext.Provider value={!!user && reauthenticationRequired}>
        {children}
      </ReauthenticationNoticeContext.Provider>
    </AuthContext.Provider>
  );
};
