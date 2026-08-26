import { Link } from 'react-router-dom';
import { Activity, Layers3, ShieldCheck } from 'lucide-react';
import { siteManifest } from '../../config/siteRuntime';

const HomeFooter = ({ manifest = siteManifest }) => {
  const legalLinks = [
    { label: 'Privacy', path: manifest.legal.privacyPath },
    { label: 'Terms', path: manifest.legal.termsPath },
    { label: 'Accessibility', path: manifest.legal.accessibilityPath },
  ];

  return (
    <footer
      aria-label="Footer"
      data-testid="base2-footer"
      className="home-integrated-footer base2-integrated-footer"
    >
      <div className="base2-footer-shell">
        <section className="base2-footer-identity" aria-labelledby="base2-footer-title">
          <div className="base2-footer-wordmark">
            <span className="base2-footer-logo" aria-hidden="true">
              <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true">
                <path d="M16 4L4 10L16 16L28 10L16 4Z" fill="currentColor" opacity="0.3" />
                <path
                  d="M4 16L16 22L28 16M4 22L16 28L28 22"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </span>
            <span>
              <small>Foundation system</small>
              <strong id="base2-footer-title">{manifest.name}</strong>
            </span>
          </div>
          <p>{manifest.seo.description}</p>
          <div className="base2-footer-proof" aria-label="Base2 delivery assurances">
            <span>
              <ShieldCheck aria-hidden="true" /> Security first
            </span>
            <span>
              <Layers3 aria-hidden="true" /> Manifest driven
            </span>
          </div>
        </section>

        <div className="base2-footer-directory">
          <nav aria-label="Footer navigation" className="base2-footer-links">
            <h2>Explore</h2>
            <ul>
              {manifest.navigation.map((item) => (
                <li key={`${item.path}:${item.label}`}>
                  <Link to={item.path}>{item.label}</Link>
                </li>
              ))}
            </ul>
          </nav>

          <nav className="base2-footer-links" aria-label="Legal">
            <h2>Policies</h2>
            <ul>
              {legalLinks.map((item) => (
                <li key={item.path}>
                  <Link to={item.path}>{item.label}</Link>
                </li>
              ))}
            </ul>
          </nav>
        </div>

        <div className="base2-footer-status" aria-label="Base2 preview status">
          <span className="base2-footer-status-label">
            <Activity aria-hidden="true" /> Preview status
          </span>
          <strong>Ready for review</strong>
          <p>
            Responsive proof, guarded operator routes, and staging-only delivery remain visible.
          </p>
          <span className="base2-footer-status-pulse">System evidence current</span>
        </div>

        <div className="base2-footer-bottom">
          <p>
            © {new Date().getUTCFullYear()} {manifest.legalName || manifest.name}
          </p>
          <span>Built to branch, verify, and roll back cleanly.</span>
        </div>
      </div>
    </footer>
  );
};

export default HomeFooter;
