import { useEffect, useRef, useState } from 'react';
import PublicShell from '../../components/public/PublicShell';
import GlassButton from '../../components/glass/GlassButton';
import { schedulingAPI } from '../../services/scheduling';

const EventsPage = () => {
  const [items, setItems] = useState([]);
  const [message, setMessage] = useState('Loading events…');
  const [bookingStates, setBookingStates] = useState({});
  const reservations = useRef(new Map());
  useEffect(() => {
    let active = true;
    schedulingAPI.list().then(
      (value) => {
        if (!active) return;
        setItems(value.items || []);
        setMessage(value.items?.length ? '' : 'No upcoming events.');
      },
      () => active && setMessage('Events are temporarily unavailable.')
    );
    return () => {
      active = false;
    };
  }, []);
  const book = async (id) => {
    if (reservations.current.has(id)) return;
    reservations.current.set(id, 'pending');
    setBookingStates((previous) => ({ ...previous, [id]: 'pending' }));
    try {
      const result = await schedulingAPI.reserve(id, 1);
      if (result?.status !== 'confirmed') throw new Error('Unconfirmed reservation');
      reservations.current.set(id, 'confirmed');
      setBookingStates((previous) => ({ ...previous, [id]: 'confirmed' }));
      setMessage('Booking confirmed.');
    } catch {
      reservations.current.delete(id);
      setBookingStates((previous) => ({ ...previous, [id]: 'failed' }));
      setMessage('Booking could not be confirmed.');
    }
  };
  return (
    <PublicShell title="Events">
      <h1>Events</h1>
      <p role="status">{message}</p>
      <ul>
        {items.map((item) => (
          <li key={item.id}>
            <h2>{item.title}</h2>
            <time dateTime={item.startsAt}>{new Date(item.startsAt).toLocaleString()}</time>
            {item.bookingOpen && (
              <GlassButton
                type="button"
                disabled={['pending', 'confirmed'].includes(bookingStates[item.id])}
                onClick={() => book(item.id)}
              >
                {bookingStates[item.id] === 'confirmed'
                  ? 'Booked'
                  : bookingStates[item.id] === 'pending'
                    ? 'Booking…'
                    : 'Book one seat'}
              </GlassButton>
            )}
          </li>
        ))}
      </ul>
    </PublicShell>
  );
};
export default EventsPage;
