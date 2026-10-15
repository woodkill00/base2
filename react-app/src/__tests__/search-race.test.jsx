import { act, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, expect, it, vi } from 'vitest';
import SearchPage from '../pages/public/SearchPage';
import { siteContentAPI } from '../services/siteContent';
import { siteManifest } from '../config/siteRuntime';

vi.mock('../services/siteContent', () => ({ siteContentAPI: { search: vi.fn() } }));
beforeEach(() => vi.resetAllMocks());

const submit = (query) => {
  fireEvent.change(screen.getByLabelText('Search this site'), { target: { value: query } });
  fireEvent.submit(screen.getByRole('search'));
};
const setup = () =>
  render(
    <MemoryRouter>
      <SearchPage manifest={{ ...siteManifest, search: { enabled: true } }} />
    </MemoryRouter>
  );
const results = (title) => ({ items: [{ id: title, title, excerpt: '', urlPath: '/about' }] });

it.each(['resolve', 'reject'])('ignores a stale request that later %ss', async (outcome) => {
  let resolve, reject;
  siteContentAPI.search.mockReturnValueOnce(
    new Promise((yes, no) => {
      resolve = yes;
      reject = no;
    })
  );
  siteContentAPI.search.mockResolvedValueOnce(results('Current result'));
  setup();
  submit('older');
  submit('newer');
  expect(await screen.findByRole('link', { name: 'Current result' })).toBeInTheDocument();
  await act(async () =>
    outcome === 'resolve' ? resolve(results('Stale result')) : reject(new Error('offline'))
  );
  expect(screen.getByRole('link', { name: 'Current result' })).toBeInTheDocument();
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});

it('does not overwrite validation with an earlier pending response', async () => {
  let resolve;
  siteContentAPI.search.mockReturnValueOnce(
    new Promise((done) => {
      resolve = done;
    })
  );
  setup();
  submit('older');
  submit('x');
  await act(async () => resolve(results('Stale result')));
  expect(screen.getByRole('alert')).toHaveTextContent('at least two');
  expect(screen.queryByRole('link', { name: 'Stale result' })).not.toBeInTheDocument();
});

it('loads the next page without losing earlier results or repeating rows', async () => {
  siteContentAPI.search.mockResolvedValueOnce({
    ...results('First result'),
    nextCursor: 'cursor-2',
  });
  siteContentAPI.search.mockResolvedValueOnce({
    items: [...results('First result').items, ...results('Second result').items],
    nextCursor: null,
  });
  setup();
  submit('guide');
  await screen.findByRole('link', { name: 'First result' });
  fireEvent.click(screen.getByRole('button', { name: 'Load more results' }));
  expect(await screen.findByRole('link', { name: 'Second result' })).toBeVisible();
  expect(screen.getAllByRole('link', { name: 'First result' })).toHaveLength(1);
  expect(siteContentAPI.search).toHaveBeenLastCalledWith('guide', 'cursor-2');
  expect(screen.queryByRole('button', { name: 'Load more results' })).not.toBeInTheDocument();
});

it('keeps earlier search results when loading more fails and allows retry', async () => {
  siteContentAPI.search.mockResolvedValueOnce({
    ...results('First result'),
    nextCursor: 'cursor-2',
  });
  siteContentAPI.search.mockRejectedValueOnce(new Error('temporary outage'));
  siteContentAPI.search.mockResolvedValueOnce({ ...results('Second result'), nextCursor: null });
  setup();
  submit('guide');
  await screen.findByRole('link', { name: 'First result' });
  fireEvent.click(screen.getByRole('button', { name: 'Load more results' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Could not load more');
  expect(screen.getByRole('link', { name: 'First result' })).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'Load more results' }));
  expect(await screen.findByRole('link', { name: 'Second result' })).toBeVisible();
});

it('does not append an old page to a newer query', async () => {
  let finishOldPage;
  siteContentAPI.search.mockResolvedValueOnce({
    ...results('First result'),
    nextCursor: 'cursor-2',
  });
  siteContentAPI.search.mockReturnValueOnce(
    new Promise((resolve) => {
      finishOldPage = resolve;
    })
  );
  siteContentAPI.search.mockResolvedValueOnce(results('New query result'));
  setup();
  submit('guide');
  await screen.findByRole('link', { name: 'First result' });
  fireEvent.click(screen.getByRole('button', { name: 'Load more results' }));
  submit('different');
  await screen.findByRole('link', { name: 'New query result' });
  await act(async () => finishOldPage(results('Old page result')));
  expect(screen.queryByRole('link', { name: 'Old page result' })).not.toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'New query result' })).toBeVisible();
});

it('rejects a repeated pagination cursor without pretending all results were loaded', async () => {
  siteContentAPI.search.mockResolvedValueOnce({
    ...results('First result'),
    nextCursor: 'cursor-2',
  });
  siteContentAPI.search.mockResolvedValueOnce({
    ...results('Duplicate page'),
    nextCursor: 'cursor-2',
  });
  setup();
  submit('guide');
  await screen.findByRole('link', { name: 'First result' });
  fireEvent.click(screen.getByRole('button', { name: 'Load more results' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Could not load more');
  expect(screen.queryByRole('link', { name: 'Duplicate page' })).not.toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'First result' })).toBeVisible();
});

it('rejects a multi-page cursor cycle', async () => {
  siteContentAPI.search.mockResolvedValueOnce({ ...results('First'), nextCursor: 'two' });
  siteContentAPI.search.mockResolvedValueOnce({ ...results('Second'), nextCursor: 'three' });
  siteContentAPI.search.mockResolvedValueOnce({ ...results('Invalid'), nextCursor: 'two' });
  setup();
  submit('guide');
  await screen.findByRole('link', { name: 'First' });
  fireEvent.click(screen.getByRole('button', { name: 'Load more results' }));
  await screen.findByRole('link', { name: 'Second' });
  fireEvent.click(screen.getByRole('button', { name: 'Load more results' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Could not load more');
  expect(screen.queryByRole('link', { name: 'Invalid' })).not.toBeInTheDocument();
});
