import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import MediaPicker from '../components/media/MediaPicker';
import { mediaLibraryAPI } from '../services/mediaLibrary';

vi.mock('../services/mediaLibrary', () => ({
  mediaLibraryAPI: { assets: vi.fn() },
}));
expect.extend(toHaveNoViolations);

beforeEach(() => {
  vi.clearAllMocks();
  mediaLibraryAPI.assets.mockResolvedValue({ items: [
    { id: 'one', filename: 'one.png', mediaType: 'image/png' },
    { id: 'two', filename: 'two.pdf', mediaType: 'application/pdf' },
  ] });
});

it('is bounded, searchable, keyboard-contained, and returns exact selections', async () => {
  const onClose = vi.fn();
  const onConfirm = vi.fn();
  const result = render(<MediaPicker open onClose={onClose} onConfirm={onConfirm} limit={1} />);
  const dialog = await screen.findByRole('dialog', { name: 'Choose media' });
  await waitFor(() => expect(screen.getByText('one.png')).toBeInTheDocument());
  fireEvent.click(screen.getByLabelText(/one.png/));
  fireEvent.click(screen.getByLabelText(/two.pdf/));
  expect(screen.getByText('1 of 1 selected')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Use selected media' }));
  expect(onConfirm).toHaveBeenCalledWith(['one']);
  fireEvent.change(screen.getByLabelText('Search media'), { target: { value: 'one' } });
  await waitFor(() => expect(mediaLibraryAPI.assets).toHaveBeenLastCalledWith(
    expect.objectContaining({ search: 'one', state: 'ready' })
  ));
  expect(await axe(result.container)).toHaveNoViolations();
  fireEvent.keyDown(dialog, { key: 'Escape' });
  expect(onClose).toHaveBeenCalled();
});

it('announces safe dependency failure without exposing raw detail', async () => {
  mediaLibraryAPI.assets.mockRejectedValue(new Error('private database detail'));
  render(<MediaPicker open onClose={vi.fn()} onConfirm={vi.fn()} />);
  expect(await screen.findByText('Media could not be loaded.')).toBeInTheDocument();
  expect(screen.queryByText(/private database detail/)).not.toBeInTheDocument();
});
