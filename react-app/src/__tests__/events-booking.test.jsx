import { act, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, expect, it, vi } from 'vitest';
import EventsPage from '../pages/public/EventsPage';
import { schedulingAPI } from '../services/scheduling';

vi.mock('../services/scheduling', () => ({ schedulingAPI: { list: vi.fn(), reserve: vi.fn() } }));
beforeEach(() => {
  vi.resetAllMocks();
  schedulingAPI.list.mockResolvedValue({
    items: [
      { id: 'one', title: 'Synthetic event', startsAt: '2030-01-01T10:00:00Z', bookingOpen: true },
    ],
  });
});

it('submits once while pending and prevents another booking after confirmation', async () => {
  let finish;
  schedulingAPI.reserve.mockReturnValue(
    new Promise((resolve) => {
      finish = resolve;
    })
  );
  render(
    <MemoryRouter>
      <EventsPage />
    </MemoryRouter>
  );
  const book = await screen.findByRole('button', { name: 'Book one seat' });
  fireEvent.click(book);
  fireEvent.click(book);
  expect(schedulingAPI.reserve).toHaveBeenCalledTimes(1);
  expect(book).toBeDisabled();
  await act(async () => finish({ status: 'confirmed' }));
  expect(screen.getByRole('button', { name: 'Booked' })).toBeDisabled();
});

it('offers retry after a rejected booking without reporting success', async () => {
  schedulingAPI.reserve
    .mockRejectedValueOnce(new Error('unavailable'))
    .mockResolvedValueOnce({ status: 'confirmed' });
  render(
    <MemoryRouter>
      <EventsPage />
    </MemoryRouter>
  );
  fireEvent.click(await screen.findByRole('button', { name: 'Book one seat' }));
  await screen.findByText('Booking could not be confirmed.');
  fireEvent.click(screen.getByRole('button', { name: 'Book one seat' }));
  expect(await screen.findByRole('button', { name: 'Booked' })).toBeDisabled();
  expect(schedulingAPI.reserve).toHaveBeenCalledTimes(2);
});

it('reports unavailable events without rendering booking actions', async () => {
  schedulingAPI.list.mockRejectedValueOnce(new Error('unavailable'));
  render(
    <MemoryRouter>
      <EventsPage />
    </MemoryRouter>
  );
  expect(await screen.findByText('Events are temporarily unavailable.')).toBeVisible();
  expect(screen.queryByRole('button', { name: 'Book one seat' })).not.toBeInTheDocument();
});

it('does not claim confirmation for an unexpected booking response', async () => {
  schedulingAPI.reserve.mockResolvedValueOnce({ status: 'pending' });
  render(
    <MemoryRouter>
      <EventsPage />
    </MemoryRouter>
  );
  fireEvent.click(await screen.findByRole('button', { name: 'Book one seat' }));
  expect(await screen.findByText('Booking could not be confirmed.')).toBeVisible();
  expect(screen.getByRole('button', { name: 'Book one seat' })).toBeEnabled();
  expect(screen.queryByText('Booking confirmed.')).not.toBeInTheDocument();
});
