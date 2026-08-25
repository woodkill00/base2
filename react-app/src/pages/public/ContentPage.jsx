import { useEffect, useState } from 'react';
import { siteContentAPI } from '../../services/siteContent';
import PublicShell from '../../components/public/PublicShell';

const ContentPage = ({ slug, fallbackTitle, locale, contentType = 'page' }) => {
  const [state, setState] = useState({ status: 'loading', item: null });

  useEffect(() => {
    let active = true;
    setState({ status: 'loading', item: null });
    const localizedSlug =
      locale && !/^en(?:-US)?$/i.test(locale) ? `${slug}-${locale.toLowerCase()}` : slug;
    const load = async () => {
      const getter =
        contentType === 'page'
          ? siteContentAPI.getPage
          : (value) => siteContentAPI.getContent(contentType, value);
      const localized = await getter(localizedSlug);
      return localized || (localizedSlug !== slug ? getter(slug) : null);
    };
    load().then(
      (item) => active && setState({ status: item ? 'ready' : 'empty', item }),
      () =>
        active && setState({ status: navigator.onLine === false ? 'offline' : 'error', item: null })
    );
    return () => {
      active = false;
    };
  }, [contentType, locale, slug]);

  return (
    <PublicShell title={fallbackTitle}>
      {state.status === 'loading' && <p role="status">Loading {fallbackTitle}…</p>}
      {state.status === 'empty' && (
        <section>
          <h1>{fallbackTitle}</h1>
          <p>This page has not been published yet.</p>
        </section>
      )}
      {state.status === 'offline' && (
        <section role="alert">
          <h1>{fallbackTitle}</h1>
          <p>You appear to be offline. This page is temporarily unavailable.</p>
        </section>
      )}
      {state.status === 'error' && (
        <section role="alert">
          <h1>{fallbackTitle}</h1>
          <p>This page is temporarily unavailable. Please try again later.</p>
        </section>
      )}
      {state.status === 'ready' && (
        <article>
          <h1>{state.item.title}</h1>
          {state.item.excerpt && <p>{state.item.excerpt}</p>}
          {String(state.item.body)
            .split(/\n{2,}/)
            .map((paragraph) => (
              <p key={paragraph}>{paragraph}</p>
            ))}
        </article>
      )}
    </PublicShell>
  );
};

export default ContentPage;
