import { render, screen } from '@testing-library/react';
import ContentPage from '../pages/public/ContentPage';
import { siteContentAPI } from '../services/siteContent';
vi.mock('../services/siteContent', () => ({ siteContentAPI: { getPage: vi.fn() } }));
vi.mock('../components/public/PublicShell', () => ({
  default: ({ children }) => <main>{children}</main>,
}));

test('explicit public body renders ordinary paragraphs as escaped text without exposing private values', async () => {
  siteContentAPI.getPage.mockResolvedValue({
    title: 'Public title',
    excerpt: 'Public excerpt',
    body: '<script>alert(1)</script>\n\nSecond paragraph',
    values: { secret: 'PRIVATE must not render' },
    metadata: {},
  });
  const { container } = render(<ContentPage slug="safe" fallbackTitle="Safe" />);
  await screen.findByRole('heading', { name: 'Public title' });
  expect(screen.getByText('<script>alert(1)</script>').tagName).toBe('P');
  expect(screen.getByText('Second paragraph').tagName).toBe('P');
  expect(container.querySelector('script')).toBeNull();
  expect(screen.queryByText('PRIVATE must not render')).not.toBeInTheDocument();
});
