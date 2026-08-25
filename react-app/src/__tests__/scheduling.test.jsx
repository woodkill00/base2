import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, expect, it, vi } from 'vitest';
import EventsPage from '../pages/public/EventsPage';
import { schedulingAPI } from '../services/scheduling';
vi.mock('../services/scheduling', () => ({ schedulingAPI: { list: vi.fn(), reserve: vi.fn() } }));
beforeEach(() => vi.clearAllMocks());
it('renders timezone-aware events and confirms a booking', async () => {
  schedulingAPI.list.mockResolvedValue({
    items: [
      { id: 'event-1', title: 'Launch', startsAt: '2026-08-26T10:00:00Z', bookingOpen: true },
    ],
  });
  schedulingAPI.reserve.mockResolvedValue({ status: 'confirmed' });
  render(
    <MemoryRouter>
      <EventsPage />
    </MemoryRouter>
  );
  fireEvent.click(await screen.findByRole('button', { name: 'Book one seat' }));
  expect(await screen.findByText('Booking confirmed.')).toBeInTheDocument();
  expect(schedulingAPI.reserve).toHaveBeenCalledWith('event-1', 1);
});
