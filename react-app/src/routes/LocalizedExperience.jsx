import { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { siteManifest } from '../config/siteRuntime';
import { resolveLocale } from '../services/privacyRuntime';
import Home from '../pages/Home';
import ContentPage from '../pages/public/ContentPage';
import ContactPage from '../pages/public/ContactPage';
import SearchPage from '../pages/public/SearchPage';
import ContentCollectionPage from '../pages/public/ContentCollectionPage';
import NotFoundPage from '../pages/public/NotFoundPage';

const LocalizedExperience = () => {
  const { locale: candidate, '*': rest = '' } = useParams();
  const resolved = resolveLocale(candidate, siteManifest);
  useEffect(() => {
    if (resolved.supported) document.documentElement.lang = resolved.locale;
  }, [resolved.locale, resolved.supported]);
  if (!resolved.supported) return <NotFoundPage />;
  const path = `/${rest}`.replace(/\/$/, '') || '/';
  if (path === '/') return <Home />;
  const pages = {
    '/about': ['about', 'About'],
    '/privacy': ['privacy', 'Privacy'],
    '/terms': ['terms', 'Terms'],
    '/accessibility': ['accessibility', 'Accessibility'],
  };
  if (pages[path])
    return (
      <ContentPage slug={pages[path][0]} fallbackTitle={pages[path][1]} locale={resolved.locale} />
    );
  if (path === '/contact') return <ContactPage />;
  if (path === '/search') return <SearchPage />;
  if (path === '/journal') return <ContentCollectionPage title="Journal" />;
  return <NotFoundPage />;
};

export default LocalizedExperience;
