import { useEffect } from 'react';
import { siteManifest } from '../../config/siteRuntime';

const canonicalHost = siteManifest.domains.find((domain) => domain.kind === 'canonical').host;

const upsertMeta = (selector, attributes) => {
  let element = document.head.querySelector(selector);
  if (!element) {
    element = document.createElement('meta');
    document.head.appendChild(element);
  }
  Object.entries(attributes).forEach(([name, value]) => element.setAttribute(name, value));
};

const PageMetadata = ({ title, description = siteManifest.seo.description }) => {
  useEffect(() => {
    const pageTitle = siteManifest.seo.titleTemplate.replace('%s', title);
    const path = window.location.pathname.startsWith('/') ? window.location.pathname : '/';
    const canonical = `https://${canonicalHost}${path}`;
    document.title = pageTitle;
    upsertMeta('meta[name="description"]', { name: 'description', content: description });
    upsertMeta('meta[name="robots"]', {
      name: 'robots',
      content: siteManifest.seo.indexing === 'allow' ? 'index,follow' : 'noindex,nofollow',
    });
    upsertMeta('meta[property="og:title"]', { property: 'og:title', content: pageTitle });
    upsertMeta('meta[property="og:description"]', {
      property: 'og:description',
      content: description,
    });
    upsertMeta('meta[property="og:url"]', { property: 'og:url', content: canonical });

    let canonicalLink = document.head.querySelector('link[rel="canonical"]');
    if (!canonicalLink) {
      canonicalLink = document.createElement('link');
      canonicalLink.setAttribute('rel', 'canonical');
      document.head.appendChild(canonicalLink);
    }
    canonicalLink.setAttribute('href', canonical);

    let structured = document.head.querySelector('script[data-runtime-seo]');
    if (!structured) {
      structured = document.createElement('script');
      structured.type = 'application/ld+json';
      structured.dataset.runtimeSeo = 'true';
      document.head.appendChild(structured);
    }
    structured.textContent = JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'WebPage',
      name: title,
      description,
      url: canonical,
      isPartOf: { '@type': 'WebSite', name: siteManifest.name, url: `https://${canonicalHost}/` },
    }).replace(/</g, '\\u003c');
  }, [description, title]);

  return null;
};

export default PageMetadata;
