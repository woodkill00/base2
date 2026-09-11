import { render, screen } from '@testing-library/react';
import RestrictedPreviewNotice from '../components/RestrictedPreviewNotice';

test('restricted preview clearly states unavailable capabilities', () => {
  render(<RestrictedPreviewNotice mode="restricted" />);
  expect(screen.getByLabelText('Preview restrictions')).toHaveTextContent(
    'uploads, media processing, and content tools are unavailable'
  );
});

test('ordinary deployments do not show restricted notice', () => {
  const { container } = render(<RestrictedPreviewNotice mode="full" />);
  expect(container).toBeEmptyDOMElement();
});
