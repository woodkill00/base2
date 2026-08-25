import { useEffect, useState } from 'react';
import PublicShell from '../../components/public/PublicShell';
import { schedulingAPI } from '../../services/scheduling';

const EventsPage = () => {
  const [items, setItems] = useState([]);
  const [message, setMessage] = useState('Loading events…');
  useEffect(() => {
    schedulingAPI.list().then(
      (value) => {
        setItems(value.items || []);
        setMessage(value.items?.length ? '' : 'No upcoming events.');
      },
      () => setMessage('Events are temporarily unavailable.')
    );
  }, []);
  const book = async (id) => {
    try {
      await schedulingAPI.reserve(id, 1);
      setMessage('Booking confirmed.');
    } catch {
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
              <button type="button" onClick={() => book(item.id)}>
                Book one seat
              </button>
            )}
          </li>
        ))}
      </ul>
    </PublicShell>
  );
};
export default EventsPage;
