import { Fragment, Suspense, useEffect } from 'react';
import { BrowserRouter as Router } from 'react-router-dom';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { MotionConfig } from 'motion/react';
import { AuthProvider } from './contexts/AuthContext';
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
        <ThemeProvider>
          <MotionConfig reducedMotion="user">
            <ToastProvider>
              <PrivacyRuntime />
              <RestrictedPreviewNotice />
              <Router
                future={{
                  v7_startTransition: true,
                  v7_relativeSplatPath: true,
                }}
              >
                <ErrorBoundary>
                  <Suspense fallback={<div style={{ padding: 24 }}>Loading...</div>}>
                    <PublicRoutes />
                  </Suspense>
                </ErrorBoundary>
              </Router>
            </ToastProvider>
          </MotionConfig>
        </ThemeProvider>
      </AuthProvider>
    </OAuthBoundary>
  );
}

export default App;
