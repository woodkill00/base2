import { Suspense, useEffect } from 'react';
import { BrowserRouter as Router } from 'react-router-dom';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { MotionConfig } from 'motion/react';
import { AuthProvider } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';
import ToastProvider from './components/ToastProvider.jsx';
import ErrorBoundary from './components/ErrorBoundary.jsx';
import PrivacyRuntime from './components/public/PrivacyRuntime.jsx';
import PublicRoutes from './routes/PublicRoutes.jsx';
import './App.css';
import { siteManifest } from './config/siteRuntime';

// Replace this with your actual Google Client ID
// Get it from: https://console.cloud.google.com/apis/credentials
const GOOGLE_CLIENT_ID = import.meta.env.REACT_APP_GOOGLE_CLIENT_ID || 'YOUR_GOOGLE_CLIENT_ID_HERE';

function App() {
  useEffect(() => {
    document.documentElement.lang = siteManifest.defaultLocale;
    document.documentElement.dataset.siteId = siteManifest.siteId;
    document.documentElement.dataset.theme = siteManifest.brand.theme;
    document.title = siteManifest.seo.titleTemplate.replace('%s', 'Home');
  }, []);

  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <AuthProvider>
        <ThemeProvider>
          <MotionConfig reducedMotion="user">
            <ToastProvider>
              <PrivacyRuntime />
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
    </GoogleOAuthProvider>
  );
}

export default App;
