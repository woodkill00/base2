import { lazy } from 'react';
import { Navigate, Route, Routes, useParams } from 'react-router-dom';
import ContentPage from '../pages/public/ContentPage';
import ContactPage from '../pages/public/ContactPage';
import SearchPage from '../pages/public/SearchPage';
import NotFoundPage from '../pages/public/NotFoundPage';
import ContentCollectionPage from '../pages/public/ContentCollectionPage';
import ProtectedRoute from '../components/ProtectedRoute';
import PermissionRoute from '../components/PermissionRoute';
import LocalizedExperience from './LocalizedExperience';
import { useAuth } from '../contexts/AuthContext';
import { siteManifest } from '../config/siteRuntime';

const Home = lazy(() => import('../pages/Home'));
const Login = lazy(() => import('../pages/Login'));
const Signup = lazy(() => import('../pages/Signup'));
const Dashboard = lazy(() => import('../pages/Dashboard.jsx'));
const Settings = lazy(() => import('../pages/SettingsCenter'));
const AdminConsole = lazy(() => import('../pages/AdminConsole'));
const AcceptInvitation = lazy(() => import('../pages/AcceptInvitation'));
const VerifyEmail = lazy(() => import('../pages/VerifyEmail'));
const ForgotPassword = lazy(() => import('../pages/ForgotPassword'));
const ResetPassword = lazy(() => import('../pages/ResetPassword'));
const EventsPage = lazy(() => import('../pages/public/EventsPage'));

const accountsEnabled = siteManifest.modules.some(
  (module) => module.id === 'accounts' && module.enabled
);

const AccountsModuleRoute = ({ children }) => (accountsEnabled ? children : <NotFoundPage />);

const moduleEnabled = (moduleId) =>
  siteManifest.modules.some((module) => module.id === moduleId && module.enabled);

const PackCollectionRoute = ({ moduleId, title, contentType, basePath }) =>
  moduleEnabled(moduleId) ? (
    <ContentCollectionPage title={title} contentType={contentType} basePath={basePath} />
  ) : (
    <NotFoundPage />
  );

const PackDetailRoute = ({ moduleId, title, contentType }) => {
  const { slug } = useParams();
  return moduleEnabled(moduleId) ? (
    <ContentPage slug={slug} fallbackTitle={title} contentType={contentType} />
  ) : (
    <NotFoundPage />
  );
};

const AdminRoute = () => {
  const { user } = useAuth();
  return (
    <PermissionRoute user={user} permission="audit.read">
      <AdminConsole user={user} />
    </PermissionRoute>
  );
};

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
    <Route
      path="/events"
      element={
        moduleEnabled('events') && moduleEnabled('booking') ? <EventsPage /> : <NotFoundPage />
      }
    />
    <Route
      path="/portfolio"
      element={
        <PackCollectionRoute
          moduleId="portfolio"
          title="Portfolio"
          contentType="portfolio-item"
          basePath="/portfolio"
        />
      }
    />
    <Route
      path="/portfolio/:slug"
      element={
        <PackDetailRoute moduleId="portfolio" title="Portfolio" contentType="portfolio-item" />
      }
    />
    <Route
      path="/blog"
      element={
        <PackCollectionRoute
          moduleId="blog"
          title="Blog"
          contentType="blog-post"
          basePath="/blog"
        />
      }
    />
    <Route
      path="/blog/:slug"
      element={<PackDetailRoute moduleId="blog" title="Blog" contentType="blog-post" />}
    />
    <Route
      path="/docs"
      element={
        <PackCollectionRoute
          moduleId="documentation"
          title="Documentation"
          contentType="doc-page"
          basePath="/docs"
        />
      }
    />
    <Route
      path="/docs/:slug"
      element={
        <PackDetailRoute moduleId="documentation" title="Documentation" contentType="doc-page" />
      }
    />
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
          <AccountsModuleRoute>
            <Navigate to="/settings/security" replace />
          </AccountsModuleRoute>
        </ProtectedRoute>
      }
    />
    <Route
      path="/admin"
      element={
        <ProtectedRoute>
          <AccountsModuleRoute>
            <AdminRoute />
          </AccountsModuleRoute>
        </ProtectedRoute>
      }
    />
    <Route
      path="/accept-invitation"
      element={
        <ProtectedRoute>
          <AccountsModuleRoute>
            <AcceptInvitation />
          </AccountsModuleRoute>
        </ProtectedRoute>
      }
    />
    <Route
      path="/settings/*"
      element={
        <ProtectedRoute>
          <Settings />
        </ProtectedRoute>
      }
    />
    <Route path="/:locale/*" element={<LocalizedExperience />} />
    <Route path="*" element={<NotFoundPage />} />
  </Routes>
);

export default PublicRoutes;
