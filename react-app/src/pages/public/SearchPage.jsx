import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import PublicShell from '../../components/public/PublicShell';
import { siteManifest } from '../../config/siteRuntime';
import { siteContentAPI } from '../../services/siteContent';
import GlassButton from '../../components/glass/GlassButton';
import GlassCard from '../../components/glass/GlassCard';
import './public-forms.css';

const SearchPage = ({ manifest = siteManifest }) => {
  const [params, setParams] = useSearchParams();
  const [query, setQuery] = useState(params.get('q') || '');
  const [state, setState] = useState({ status: 'idle', items: [] });
  const requestGeneration = useRef(0);
  const submittedQuery = useRef('');
  const morePending = useRef(false);
  const seenCursors = useRef(new Set());
  useEffect(
    () => () => {
      requestGeneration.current += 1;
    },
    []
  );

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
    const generation = ++requestGeneration.current;
    morePending.current = false;
    seenCursors.current = new Set();
    if (query.trim().length < 2) return setState({ status: 'invalid', items: [] });
    setParams({ q: query.trim() });
    submittedQuery.current = query.trim();
    setState({ status: 'loading', items: [] });
    try {
      const page = await siteContentAPI.search(query.trim());
      if (generation !== requestGeneration.current) return;
      setState({
        status: page.items.length ? 'ready' : 'empty',
        items: page.items,
        cursor: page.nextCursor,
      });
    } catch (_) {
      if (generation !== requestGeneration.current) return;
      setState({ status: navigator.onLine === false ? 'offline' : 'error', items: [] });
    }
  };

  const loadMore = async () => {
    if (!state.cursor || morePending.current) return;
    const generation = requestGeneration.current;
    const cursor = state.cursor;
    morePending.current = true;
    setState((previous) => ({ ...previous, loadingMore: true, moreError: false }));
    try {
      const page = await siteContentAPI.search(submittedQuery.current, cursor);
      if (generation !== requestGeneration.current) return;
      if (
        page.nextCursor &&
        (page.nextCursor === cursor || seenCursors.current.has(page.nextCursor))
      ) {
        throw new Error('Repeated search cursor');
      }
      seenCursors.current.add(cursor);
      setState((previous) => ({
        ...previous,
        items: [
          ...new Map([...previous.items, ...page.items].map((item) => [item.id, item])).values(),
        ],
        cursor: page.nextCursor,
        loadingMore: false,
      }));
    } catch {
      if (generation === requestGeneration.current)
        setState((previous) => ({ ...previous, loadingMore: false, moreError: true }));
    } finally {
      if (generation === requestGeneration.current) morePending.current = false;
    }
  };

  return (
    <PublicShell title="Search">
      <GlassCard className="public-form-panel">
        <h1>Search</h1>
        <form role="search" onSubmit={submit}>
          <label htmlFor="site-search">Search this site</label>
          <input
            className="base2-input"
            id="site-search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <GlassButton type="submit">Search</GlassButton>
        </form>
        {state.status === 'loading' && <p role="status">Searching…</p>}
        {state.status === 'invalid' && <p role="alert">Enter at least two characters.</p>}
        {state.status === 'empty' && <p>No results found.</p>}
        {state.status === 'offline' && <p role="alert">Search is unavailable while offline.</p>}
        {state.status === 'error' && <p role="alert">Search is temporarily unavailable.</p>}
        {state.status === 'ready' && (
          <ul className="public-search-results">
            {state.items.map((item) => (
              <li key={item.id}>
                <h2>
                  <a href={item.urlPath}>{item.title}</a>
                </h2>
                <p>{item.excerpt}</p>
              </li>
            ))}
          </ul>
        )}
        {state.moreError && <p role="alert">Could not load more results. Please try again.</p>}
        {state.status === 'ready' && state.cursor && (
          <GlassButton onClick={loadMore} disabled={state.loadingMore}>
            {state.loadingMore ? 'Loading more…' : 'Load more results'}
          </GlassButton>
        )}
      </GlassCard>
    </PublicShell>
  );
};

export default SearchPage;
