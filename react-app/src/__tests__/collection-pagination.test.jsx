import { act, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, expect, it, vi } from 'vitest';
import ContentCollectionPage from '../pages/public/ContentCollectionPage';
import { siteContentAPI } from '../services/siteContent';

vi.mock('../services/siteContent', () => ({ siteContentAPI: { listContent: vi.fn() } }));
beforeEach(() => vi.resetAllMocks());
const row = (id) => ({ id, title: id, slug: id, excerpt: '' });
const view = (type = 'article') => (
  <MemoryRouter>
    <ContentCollectionPage title="Journal" contentType={type} basePath="/journal" />
  </MemoryRouter>
);

it('loads and deduplicates subsequent collection pages', async () => {
  siteContentAPI.listContent.mockResolvedValueOnce({ items: [row('first')], nextCursor: 'two' });
  siteContentAPI.listContent.mockResolvedValueOnce({
    items: [row('first'), row('second')],
    nextCursor: null,
  });
  render(view());
  await screen.findByRole('link', { name: 'Read first' });
  fireEvent.click(screen.getByRole('button', { name: 'Load more content' }));
  expect(await screen.findByRole('link', { name: 'Read second' })).toBeVisible();
  expect(screen.getAllByRole('link', { name: 'Read first' })).toHaveLength(1);
  expect(siteContentAPI.listContent).toHaveBeenLastCalledWith('two', 'article');
  expect(screen.queryByRole('button', { name: 'Load more content' })).not.toBeInTheDocument();
});

it('preserves rows and allows retry after a failed page', async () => {
  siteContentAPI.listContent.mockResolvedValueOnce({ items: [row('first')], nextCursor: 'two' });
  siteContentAPI.listContent.mockRejectedValueOnce(new Error('offline'));
  siteContentAPI.listContent.mockResolvedValueOnce({ items: [row('second')] });
  render(view());
  await screen.findByRole('link', { name: 'Read first' });
  fireEvent.click(screen.getByRole('button', { name: 'Load more content' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Could not load more');
  expect(screen.getByRole('link', { name: 'Read first' })).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'Load more content' }));
  expect(await screen.findByRole('link', { name: 'Read second' })).toBeVisible();
});

it('ignores pending pages after changing collection and blocks duplicate submissions', async () => {
  let finish;
  siteContentAPI.listContent.mockResolvedValueOnce({ items: [row('first')], nextCursor: 'two' });
  siteContentAPI.listContent.mockReturnValueOnce(
    new Promise((resolve) => {
      finish = resolve;
    })
  );
  siteContentAPI.listContent.mockResolvedValueOnce({ items: [row('new')] });
  const { rerender } = render(view());
  await screen.findByRole('link', { name: 'Read first' });
  const more = screen.getByRole('button', { name: 'Load more content' });
  fireEvent.click(more);
  fireEvent.click(more);
  expect(siteContentAPI.listContent).toHaveBeenCalledTimes(2);
  rerender(view('project'));
  await screen.findByRole('link', { name: 'Read new' });
  await act(async () => finish({ items: [row('stale')] }));
  expect(screen.queryByRole('link', { name: 'Read stale' })).not.toBeInTheDocument();
});

it('rejects cursor cycles rather than silently presenting a complete collection', async () => {
  siteContentAPI.listContent.mockResolvedValueOnce({ items: [row('first')], nextCursor: 'two' });
  siteContentAPI.listContent.mockResolvedValueOnce({ items: [row('second')], nextCursor: 'three' });
  siteContentAPI.listContent.mockResolvedValueOnce({ items: [row('bad')], nextCursor: 'two' });
  render(view());
  await screen.findByRole('link', { name: 'Read first' });
  fireEvent.click(screen.getByRole('button', { name: 'Load more content' }));
  await screen.findByRole('link', { name: 'Read second' });
  fireEvent.click(screen.getByRole('button', { name: 'Load more content' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Could not load more');
  expect(screen.queryByRole('link', { name: 'Read bad' })).not.toBeInTheDocument();
});
