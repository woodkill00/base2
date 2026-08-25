import { Link } from 'react-router-dom';
import PublicShell from '../../components/public/PublicShell';
import { siteManifest } from '../../config/siteRuntime';

const NotFoundPage = () => (
  <PublicShell title="Page not found">
    <h1>Page not found</h1>
    <p>{siteManifest.name} could not find the page you requested.</p>
    <Link to="/">Return home</Link>
  </PublicShell>
);

export default NotFoundPage;
