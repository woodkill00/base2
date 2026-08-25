import { lazy } from 'react';
import { Route, Routes } from 'react-router-dom';
import ContentPage from '../pages/public/ContentPage';
import ContactPage from '../pages/public/ContactPage';
import SearchPage from '../pages/public/SearchPage';
import NotFoundPage from '../pages/public/NotFoundPage';
import ContentCollectionPage from '../pages/public/ContentCollectionPage';
import ProtectedRoute from '../components/ProtectedRoute';

const Home = lazy(() => import('../pages/Home'));
const Login = lazy(() => import('../pages/Login'));
const Signup = lazy(() => import('../pages/Signup'));
const Dashboard = lazy(() => import('../pages/Dashboard.jsx'));
const Settings = lazy(() => import('../pages/Settings'));
const VerifyEmail = lazy(() => import('../pages/VerifyEmail'));
const ForgotPassword = lazy(() => import('../pages/ForgotPassword'));
const ResetPassword = lazy(() => import('../pages/ResetPassword'));

const PublicRoutes = () => (
  <Routes>
    <Route path="/" element={<Home />} />
    <Route path="/about" element={<ContentPage slug="about" fallbackTitle="About" />} />
    <Route path="/privacy" element={<ContentPage slug="privacy" fallbackTitle="Privacy" />} />
    <Route path="/terms" element={<ContentPage slug="terms" fallbackTitle="Terms" />} />
    <Route
      path="/accessibility"
      element={<ContentPage slug="accessibility" fallbackTitle="Accessibility" />}
    />
    <Route path="/contact" element={<ContactPage />} />
    <Route path="/search" element={<SearchPage />} />
    <Route path="/journal" element={<ContentCollectionPage title="Journal" />} />
    <Route path="/login" element={<Login variant="public" />} />
    <Route path="/signup" element={<Signup variant="public" />} />
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
      path="/account"
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
    <Route path="*" element={<NotFoundPage />} />
  </Routes>
);

export default PublicRoutes;
