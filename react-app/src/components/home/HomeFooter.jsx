import { Link } from 'react-router-dom';
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
      className="home-integrated-footer backdrop-blur-2xl bg-white/20 dark:bg-black/30 border-t border-white/30 dark:border-white/20"
      style={{ marginTop: 'calc(4rem)' }}
    >
      <div style={{ padding: 'calc(3rem) calc(max(1rem, calc((100vw - 1200px) / 2))) calc(2rem)' }}>
        <div
          className="grid gap-8 mb-8"
          style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}
        >
          <div>
            <div className="flex items-center gap-2 mb-4">
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
              <span className="text-lg font-medium">{manifest.name}</span>
            </div>
            <p className="text-sm text-foreground/60 dark:text-foreground/50 mb-4">
              {manifest.seo.description}
            </p>
          </div>

          <nav aria-label="Footer navigation">
            <h2 className="font-medium mb-3">Explore</h2>
            <ul className="space-y-2">
              {manifest.navigation.map((item) => (
                <li key={`${item.path}:${item.label}`}>
                  <Link className="text-sm text-foreground/60 hover:text-foreground" to={item.path}>
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        </div>

        <div className="pt-6 border-t border-white/20 dark:border-white/10 flex flex-col sm:flex-row justify-between items-center gap-4">
          <p className="text-sm text-foreground/50">
            © {new Date().getUTCFullYear()} {manifest.legalName || manifest.name}
          </p>
          <nav className="flex gap-6" aria-label="Legal">
            {legalLinks.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className="text-sm text-foreground/50 hover:text-foreground focus-visible:underline"
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </div>
    </footer>
  );
};

export default HomeFooter;
