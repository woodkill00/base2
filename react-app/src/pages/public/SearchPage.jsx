import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import PublicShell from '../../components/public/PublicShell';
import { siteManifest } from '../../config/siteRuntime';
import { siteContentAPI } from '../../services/siteContent';

const SearchPage = ({ manifest = siteManifest }) => {
  const [params, setParams] = useSearchParams();
  const [query, setQuery] = useState(params.get('q') || '');
  const [state, setState] = useState({ status: 'idle', items: [] });

  if (!manifest.search.enabled) {
    return (
      <PublicShell title="Search">
        <h1>Search</h1>
        <p>Search is not enabled for this site.</p>
      </PublicShell>
    );
  }

  const submit = async (event) => {
    event.preventDefault();
    if (query.trim().length < 2) return setState({ status: 'invalid', items: [] });
    setParams({ q: query.trim() });
    setState({ status: 'loading', items: [] });
    try {
      const page = await siteContentAPI.search(query.trim());
      setState({ status: page.items.length ? 'ready' : 'empty', items: page.items });
    } catch (_) {
      setState({ status: navigator.onLine === false ? 'offline' : 'error', items: [] });
    }
  };

  return (
    <PublicShell title="Search">
      <h1>Search</h1>
      <form role="search" onSubmit={submit}>
        <label htmlFor="site-search">Search this site</label>
        <input id="site-search" value={query} onChange={(event) => setQuery(event.target.value)} />
        <button type="submit">Search</button>
      </form>
      {state.status === 'loading' && <p role="status">Searching…</p>}
      {state.status === 'invalid' && <p role="alert">Enter at least two characters.</p>}
      {state.status === 'empty' && <p>No results found.</p>}
      {state.status === 'offline' && <p role="alert">Search is unavailable while offline.</p>}
      {state.status === 'error' && <p role="alert">Search is temporarily unavailable.</p>}
      {state.status === 'ready' && (
        <ul>
          {state.items.map((item) => (
            <li key={item.id}>
              <a href={item.urlPath}>{item.title}</a>
              <p>{item.excerpt}</p>
            </li>
          ))}
        </ul>
      )}
    </PublicShell>
  );
};

export default SearchPage;
