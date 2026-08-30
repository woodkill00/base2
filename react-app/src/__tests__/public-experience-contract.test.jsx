import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import PublicRoutes from '../routes/PublicRoutes';
import ContactPage from '../pages/public/ContactPage';
import SearchPage from '../pages/public/SearchPage';
import ContentCollectionPage from '../pages/public/ContentCollectionPage';
import { siteContentAPI } from '../services/siteContent';
import { siteManifest } from '../config/siteRuntime';

vi.mock('../services/siteContent', () => ({
  siteContentAPI: {
    getPage: vi.fn(),
    listContent: vi.fn(),
    search: vi.fn(),
    submitForm: vi.fn(),
  },
}));

const renderRoute = (path) =>
  render(
    <MemoryRouter
      initialEntries={[path]}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <PublicRoutes />
    </MemoryRouter>
  );

describe('manifest public experience contract', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    document.documentElement.lang = siteManifest.defaultLocale;
  });

  it.each([
    ['/about', 'About'],
    ['/privacy', 'Privacy'],
    ['/terms', 'Terms'],
    ['/accessibility', 'Accessibility'],
  ])('renders published %s content', async (path, title) => {
    siteContentAPI.getPage.mockResolvedValue({ title, body: `${title} body`, excerpt: '' });
    renderRoute(path);
    expect(await screen.findByRole('heading', { name: title })).toBeInTheDocument();
    expect(screen.getByText(`${title} body`)).toBeInTheDocument();
  });

  it('loads localized content first and falls back to the base publication', async () => {
    siteContentAPI.getPage.mockResolvedValueOnce(null).mockResolvedValueOnce({
      title: 'Datenschutz',
      body: 'Verified fallback content',
      excerpt: '',
    });
    renderRoute('/de/privacy');
    expect(await screen.findByRole('heading', { name: 'Datenschutz' })).toBeInTheDocument();
    expect(siteContentAPI.getPage.mock.calls.map(([slug]) => slug)).toEqual([
      'privacy-de',
      'privacy',
    ]);
    expect(document.documentElement.lang).toBe('de');
  });

  it('exposes deterministic loading, empty, unavailable, and offline states', async () => {
    let resolve;
    siteContentAPI.getPage.mockReturnValue(
      new Promise((done) => {
        resolve = done;
      })
    );
    const view = renderRoute('/about');
    expect(screen.getByRole('status')).toHaveTextContent('Loading');
    await act(async () => resolve(null));
    expect(await screen.findByText(/not been published/i)).toBeInTheDocument();
    view.unmount();

    siteContentAPI.getPage.mockRejectedValueOnce(new Error('network'));
    renderRoute('/privacy');
    expect(await screen.findByRole('alert')).toHaveTextContent(/temporarily unavailable/i);
  });

  it('submits the contact form once and presents a receipt', async () => {
    const user = userEvent.setup();
    siteContentAPI.submitForm.mockResolvedValue({
      id: 'receipt-1',
      status: 'pending',
      replayed: false,
    });
    renderRoute('/contact');
    await act(async () => {
      await user.type(screen.getByLabelText('Name'), 'Avery');
      await user.type(screen.getByLabelText('Email'), 'avery@example.test');
      await user.type(screen.getByLabelText('Message'), 'Please send details.');
      await user.click(screen.getByRole('button', { name: 'Send message' }));
    });
    expect(await screen.findByRole('status')).toHaveTextContent(/received/i);
    expect(siteContentAPI.submitForm).toHaveBeenCalledTimes(1);
  });

  it('shows an explicit disabled search state when the manifest disables search', () => {
    renderRoute('/search');
    expect(screen.getByRole('heading', { name: 'Search' })).toBeInTheDocument();
    expect(screen.getByText(/not enabled/i)).toBeInTheDocument();
    expect(siteContentAPI.search).not.toHaveBeenCalled();
  });

  it('searches an enabled profile and reports results, empty, validation, and failure', async () => {
    const enabledManifest = { ...siteManifest, search: { enabled: true } };
    const user = userEvent.setup();
    siteContentAPI.search.mockResolvedValueOnce({
      items: [{ id: 'result-1', title: 'Field Guide', excerpt: 'A guide', urlPath: '/guide' }],
    });
    const view = render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <SearchPage manifest={enabledManifest} />
      </MemoryRouter>
    );
    await act(async () => {
      await user.type(screen.getByLabelText('Search this site'), 'guide');
      await user.click(screen.getByRole('button', { name: 'Search' }));
    });
    expect(await screen.findByRole('link', { name: 'Field Guide' })).toHaveAttribute(
      'href',
      '/guide'
    );

    siteContentAPI.search.mockResolvedValueOnce({ items: [] });
    await act(async () => user.click(screen.getByRole('button', { name: 'Search' })));
    expect(await screen.findByText('No results found.')).toBeInTheDocument();
    await act(async () => {
      await user.clear(screen.getByLabelText('Search this site'));
      await user.type(screen.getByLabelText('Search this site'), 'x');
      await user.click(screen.getByRole('button', { name: 'Search' }));
    });
    expect(screen.getByRole('alert')).toHaveTextContent('at least two');
    view.unmount();

    siteContentAPI.search.mockRejectedValueOnce(new Error('network'));
    render(
      <MemoryRouter
        initialEntries={['/search?q=broken']}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <SearchPage manifest={enabledManifest} />
      </MemoryRouter>
    );
    await act(async () => user.click(screen.getByRole('button', { name: 'Search' })));
    expect(await screen.findByRole('alert')).toHaveTextContent('temporarily unavailable');
  });

  it('renders journal ready and empty states and explicit disabled contact policy', async () => {
    siteContentAPI.listContent.mockResolvedValueOnce({
      items: [{ id: 'entry-1', title: 'First entry', excerpt: 'Published excerpt' }],
    });
    const view = render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <ContentCollectionPage title="Journal" />
      </MemoryRouter>
    );
    expect(await screen.findByRole('heading', { name: 'First entry' })).toBeInTheDocument();
    view.unmount();

    siteContentAPI.listContent.mockResolvedValueOnce({ items: [] });
    const empty = render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <ContentCollectionPage title="Journal" />
      </MemoryRouter>
    );
    expect(await screen.findByText(/No published content/i)).toBeInTheDocument();
    empty.unmount();

    const disabledManifest = {
      ...siteManifest,
      contact: { ...siteManifest.contact, enabled: false },
    };
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <ContactPage manifest={disabledManifest} />
      </MemoryRouter>
    );
    expect(screen.getByText(/not enabled/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Send message' })).not.toBeInTheDocument();
  });

  it('renders a branded not-found page with a working return control', () => {
    renderRoute('/missing-page');
    expect(screen.getByRole('heading', { name: 'Page not found' })).toBeInTheDocument();
    expect(
      screen.getByText('Ember Studio could not find the page you requested.')
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Return home' })).toHaveAttribute('href', '/');
    expect(document.title).toBe('Page not found · Ember Studio');
    expect(document.head.querySelector('link[rel="canonical"]')).toHaveAttribute(
      'href',
      'https://ember.example/'
    );
    expect(document.head.querySelector('script[data-runtime-seo]')).toHaveAttribute(
      'type',
      'application/ld+json'
    );
  });
});
