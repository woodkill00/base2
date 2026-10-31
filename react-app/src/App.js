import { Fragment, Suspense, useEffect } from 'react';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';
import ToastProvider from './components/ToastProvider.jsx';
import ErrorBoundary from './components/ErrorBoundary.jsx';
import PrivacyRuntime from './components/public/PrivacyRuntime.jsx';
import RestrictedPreviewNotice from './components/RestrictedPreviewNotice.jsx';
import PublicRoutes from './routes/PublicRoutes.jsx';
import './App.css';
import { siteManifest } from './config/siteRuntime';
import { resolveLocale } from './services/privacyRuntime';
import { getGoogleClientId } from './services/googleAuthConfig';

// Replace this with your actual Google Client ID
// Get it from: https://console.cloud.google.com/apis/credentials

function AccountAppearance({ children }) {
  const { user, loading } = useAuth();
  return (
    <ThemeProvider accountId={user?.id} authenticationLoading={loading}>
      {children}
    </ThemeProvider>
  );
}

// One stable router owns browser history across account/theme updates. Existing
// descendant routes and provider/error boundaries remain unchanged.
const router = createBrowserRouter([
  {
    path: '*',
    element: (
      <ErrorBoundary>
        <Suspense fallback={<div style={{ padding: 24 }}>Loading...</div>}>
          <PublicRoutes />
        </Suspense>
      </ErrorBoundary>
    ),
  },
]);

function App() {
  const clientId = getGoogleClientId();
  const OAuthBoundary = clientId ? GoogleOAuthProvider : Fragment;
  useEffect(() => {
    const routeLocale = resolveLocale(window.location.pathname.split('/')[1], siteManifest);
    const activeLocale = routeLocale.supported ? routeLocale.locale : siteManifest.defaultLocale;
    document.documentElement.lang = activeLocale;
    document.documentElement.dir = activeLocale === 'ar' ? 'rtl' : 'ltr';
    document.documentElement.dataset.siteId = siteManifest.siteId;
    document.documentElement.dataset.theme = siteManifest.brand.theme;
    document.title = siteManifest.seo.titleTemplate.replace('%s', 'Home');
  }, []);

  return (
    <OAuthBoundary {...(clientId ? { clientId } : {})}>
      <AuthProvider>
        <AccountAppearance>
          <ToastProvider>
            <PrivacyRuntime />
            <RestrictedPreviewNotice />
            <RouterProvider router={router} />
          </ToastProvider>
        </AccountAppearance>
      </AuthProvider>
    </OAuthBoundary>
  );
}

export default App;
