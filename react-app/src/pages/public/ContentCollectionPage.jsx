import { useEffect, useState } from 'react';
import PublicShell from '../../components/public/PublicShell';
import { siteContentAPI } from '../../services/siteContent';

const ContentCollectionPage = ({ title }) => {
  const [state, setState] = useState({ status: 'loading', items: [] });

  useEffect(() => {
    let active = true;
    siteContentAPI.listContent().then(
      (page) =>
        active && setState({ status: page.items.length ? 'ready' : 'empty', items: page.items }),
      () =>
        active && setState({ status: navigator.onLine === false ? 'offline' : 'error', items: [] })
    );
    return () => {
      active = false;
    };
  }, []);

  return (
    <PublicShell title={title}>
      <h1>{title}</h1>
      {state.status === 'loading' && <p role="status">Loading content…</p>}
      {state.status === 'empty' && <p>No published content is available.</p>}
      {state.status === 'offline' && <p role="alert">Content is unavailable while offline.</p>}
      {state.status === 'error' && <p role="alert">Content is temporarily unavailable.</p>}
      {state.status === 'ready' && (
        <ul>
          {state.items.map((item) => (
            <li key={item.id}>
              <h2>{item.title}</h2>
              <p>{item.excerpt}</p>
            </li>
          ))}
        </ul>
      )}
    </PublicShell>
  );
};

export default ContentCollectionPage;
