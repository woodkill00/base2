import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import ContentCollectionPage from '../pages/public/ContentCollectionPage';
import ContentPage from '../pages/public/ContentPage';
import { siteContentAPI } from '../services/siteContent';

vi.mock('../services/siteContent', () => ({
  siteContentAPI: {
    listContent: vi.fn(),
    getPage: vi.fn(),
    getContent: vi.fn(),
  },
}));

describe('declarative content packs', () => {
  beforeEach(() => vi.clearAllMocks());

  for (const pack of [
    ['Portfolio', 'portfolio-item', '/portfolio'],
    ['Blog', 'blog-post', '/blog'],
    ['Documentation', 'doc-page', '/docs'],
  ]) {
    it(`renders and filters the ${pack[0]} collection`, async () => {
      siteContentAPI.listContent.mockResolvedValue({
        items: [{ id: pack[1], slug: 'first', title: `${pack[0]} entry`, excerpt: 'Safe' }],
      });
      render(
        <MemoryRouter>
          <ContentCollectionPage title={pack[0]} contentType={pack[1]} basePath={pack[2]} />
        </MemoryRouter>
      );
      expect(await screen.findByRole('heading', { name: `${pack[0]} entry` })).toBeInTheDocument();
      expect(siteContentAPI.listContent).toHaveBeenCalledWith(undefined, pack[1]);
      expect(screen.getByRole('link', { name: `Read ${pack[0]} entry` })).toHaveAttribute(
        'href',
        `${pack[2]}/first`
      );
    });
  }

  it('loads a detail through the exact pack content type', async () => {
    siteContentAPI.getContent.mockResolvedValue({
      title: 'Typed entry',
      excerpt: '',
      body: 'Body',
    });
    render(
      <MemoryRouter>
        <ContentPage slug="typed" fallbackTitle="Blog" contentType="blog-post" />
      </MemoryRouter>
    );
    expect(await screen.findByRole('heading', { name: 'Typed entry' })).toBeInTheDocument();
    expect(siteContentAPI.getContent).toHaveBeenCalledWith('blog-post', 'typed');
  });
});
