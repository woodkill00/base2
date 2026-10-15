import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import PublicShell from '../../components/public/PublicShell';
import { siteContentAPI } from '../../services/siteContent';
import { PublicWorkspaceFields } from '../../components/content/PublicFieldRenderer';
import GlassButton from '../../components/glass/GlassButton';

const ContentCollectionPage = ({ title, contentType, basePath }) => {
  const [state, setState] = useState({ status: 'loading', items: [] });
  const generation = useRef(0);
  const loadingMore = useRef(false);
  const seenCursors = useRef(new Set());

  useEffect(() => {
    let active = true;
    generation.current += 1;
    loadingMore.current = false;
    seenCursors.current = new Set();
    setState({ status: 'loading', items: [] });
    siteContentAPI.listContent(undefined, contentType).then(
      (page) =>
        active &&
        setState({
          status: page.items.length || page.nextCursor ? 'ready' : 'empty',
          items: page.items,
          nextCursor: page.nextCursor,
        }),
      () =>
        active && setState({ status: navigator.onLine === false ? 'offline' : 'error', items: [] })
    );
    return () => {
      active = false;
      generation.current += 1;
    };
  }, [contentType]);

  const loadMore = async () => {
    if (loadingMore.current || !state.nextCursor) return;
    loadingMore.current = true;
    const current = generation.current;
    const cursor = state.nextCursor;
    setState((previous) => ({ ...previous, busy: true, pageError: false }));
    try {
      const page = await siteContentAPI.listContent(cursor, contentType);
      if (current !== generation.current) return;
      if (
        page.nextCursor &&
        (page.nextCursor === cursor || seenCursors.current.has(page.nextCursor))
      ) {
        throw new Error('Pagination cursor cycle');
      }
      seenCursors.current.add(cursor);
      setState((previous) => ({
        ...previous,
        items: [
          ...new Map([...previous.items, ...page.items].map((item) => [item.id, item])).values(),
        ],
        nextCursor: page.nextCursor,
        busy: false,
      }));
    } catch {
      if (current === generation.current)
        setState((previous) => ({ ...previous, busy: false, pageError: true }));
    } finally {
      if (current === generation.current) loadingMore.current = false;
    }
  };

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
              <PublicWorkspaceFields item={item} />
              {basePath && (
                <Link to={`${basePath}/${encodeURIComponent(item.slug)}`}>Read {item.title}</Link>
              )}
            </li>
          ))}
        </ul>
      )}
      {state.pageError && <p role="alert">Could not load more content. Please retry.</p>}
      {state.nextCursor && (
        <GlassButton type="button" disabled={state.busy} onClick={loadMore}>
          {state.busy ? 'Loading more content…' : 'Load more content'}
        </GlassButton>
      )}
    </PublicShell>
  );
};

export default ContentCollectionPage;
