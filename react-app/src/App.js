import { Suspense, lazy, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { AuthProvider } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';
import ToastProvider from './components/ToastProvider.jsx';
import ProtectedRoute from './components/ProtectedRoute.jsx';
import ErrorBoundary from './components/ErrorBoundary.jsx';
import './App.css';
import { siteManifest } from './config/siteRuntime';
const Home = lazy(() => import('./pages/Home'));
const Login = lazy(() => import('./pages/Login'));
const Signup = lazy(() => import('./pages/Signup'));
const Items = lazy(() => import('./pages/Items'));
const Dashboard = lazy(() => import('./pages/Dashboard.jsx'));
const Settings = lazy(() => import('./pages/Settings'));
const VerifyEmail = lazy(() => import('./pages/VerifyEmail'));
const ForgotPassword = lazy(() => import('./pages/ForgotPassword'));
const ResetPassword = lazy(() => import('./pages/ResetPassword'));

// Replace this with your actual Google Client ID
// Get it from: https://console.cloud.google.com/apis/credentials
const GOOGLE_CLIENT_ID = import.meta.env.REACT_APP_GOOGLE_CLIENT_ID || 'YOUR_GOOGLE_CLIENT_ID_HERE';

function App() {
  useEffect(() => {
    document.documentElement.lang = siteManifest.defaultLocale;
    document.documentElement.dataset.siteId = siteManifest.siteId;
    document.title = siteManifest.seo.titleTemplate.replace('%s', 'Home');
  }, []);

  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <AuthProvider>
        <ThemeProvider>
          <ToastProvider>
            <Router
              future={{
                v7_startTransition: true,
                v7_relativeSplatPath: true,
              }}
            >
              <ErrorBoundary>
                <Suspense fallback={<div style={{ padding: 24 }}>Loading...</div>}>
                  <Routes>
                    <Route path="/" element={<Home />} />
                    <Route path="/login" element={<Login variant="public" />} />
                    <Route path="/signup" element={<Signup variant="public" />} />
                    <Route path="/items" element={<Items />} />
                    <Route path="/verify-email" element={<VerifyEmail variant="public" />} />
                    <Route path="/forgot-password" element={<ForgotPassword variant="public" />} />
                    <Route path="/reset-password" element={<ResetPassword variant="public" />} />
                    <Route
                      path="/dashboard"
                      element={
                        <ProtectedRoute>
                          <Dashboard />
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/settings"
                      element={
                        <ProtectedRoute>
                          <Settings />
                        </ProtectedRoute>
                      }
                    />
                  </Routes>
                </Suspense>
              </ErrorBoundary>
            </Router>
          </ToastProvider>
        </ThemeProvider>
      </AuthProvider>
    </GoogleOAuthProvider>
  );
}

export default App;
