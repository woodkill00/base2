import { createRef } from 'react';
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
  const returnFocusRef = createRef();
  render(<><button ref={returnFocusRef}>Open picker</button><MediaPicker open onClose={onClose} onConfirm={onConfirm} limit={1} returnFocusRef={returnFocusRef} /></>);
  const dialog = await screen.findByRole('dialog', { name: 'Choose media' });
  await waitFor(() => expect(screen.getByText('one.png')).toBeInTheDocument());
  const close = screen.getByRole('button', { name: 'Close' });
  expect(close).toHaveFocus();
  fireEvent.keyDown(dialog, { key: 'Tab', shiftKey: true });
  expect(screen.getByLabelText(/two.pdf/)).toHaveFocus();
  fireEvent.click(screen.getByLabelText(/one.png/));
  const selectionStatus = screen.getByText('1 of 1 selected');
  expect(selectionStatus.closest('p')).toHaveAttribute('dir', 'ltr');
  expect(selectionStatus.closest('p')).toHaveAttribute('lang', 'en');
  expect(selectionStatus).toHaveAttribute('dir', 'ltr');
  fireEvent.click(screen.getByLabelText(/two.pdf/));
  expect(screen.getByText('Selection limit reached. Choose no more than 1.')).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Search media'), { target: { value: 'one' } });
  fireEvent.change(screen.getByLabelText('Status'), { target: { value: 'archived' } });
  await waitFor(() => expect(mediaLibraryAPI.assets).toHaveBeenLastCalledWith(
    expect.objectContaining({ search: 'one', state: 'archived' })
  ));
  screen.getByRole('button', { name: 'Use selected media' }).focus();
  fireEvent.keyDown(dialog, { key: 'Tab' });
  expect(close).toHaveFocus();
  expect(await axe(document.body)).toHaveNoViolations();
  fireEvent.click(screen.getByRole('button', { name: 'Use selected media' }));
  expect(onConfirm).toHaveBeenCalledWith(['one']);
  expect(onClose).toHaveBeenCalled();
  await waitFor(() => expect(returnFocusRef.current).toHaveFocus());
});

it('announces safe dependency failure without exposing raw detail', async () => {
  mediaLibraryAPI.assets.mockRejectedValue(new Error('private database detail'));
  render(<MediaPicker open onClose={vi.fn()} onConfirm={vi.fn()} />);
  expect(await screen.findByText('Media could not be loaded.')).toBeInTheDocument();
  expect(screen.queryByText(/private database detail/)).not.toBeInTheDocument();
});

it('announces an empty result and closes with Escape', async () => {
  const onClose = vi.fn();
  mediaLibraryAPI.assets.mockResolvedValue({ items: [] });
  render(<MediaPicker open onClose={onClose} onConfirm={vi.fn()} />);
  const dialog = await screen.findByRole('dialog', { name: 'Choose media' });
  expect(await screen.findByText('No matching media. Change the search or status filter.')).toBeInTheDocument();
  fireEvent.keyDown(dialog, { key: 'Escape' });
  expect(onClose).toHaveBeenCalledOnce();
});
