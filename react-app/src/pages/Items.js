import React, { useEffect, useState } from 'react';
import { itemsAPI } from '../services/items';

export default function Items() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await itemsAPI.list();
      setItems(data);
    } catch (e) {
      setError('Failed to load items');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const onCreate = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    try {
      if (!name.trim()) {
        setError('Name is required');
        return;
      }
      await itemsAPI.create(name.trim(), description.trim());
      setName('');
      setDescription('');
      setSuccess('Item created successfully');
      await load();
    } catch (e) {
      setError('Failed to create item');
    }
  };

  return (
    <div style={{ maxWidth: 800, margin: '40px auto', padding: 20 }}>
      <h1>Items</h1>
      <p>Backed by Django models, served via FastAPI.</p>

      <form onSubmit={onCreate} style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            type="text"
            placeholder="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            style={{ flex: 1, padding: 8 }}
          />
          <input
            type="text"
            placeholder="Description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            style={{ flex: 2, padding: 8 }}
          />
          <button type="submit">Add</button>
        </div>
      </form>

      {success && (
        <div style={{ color: 'green', marginBottom: 10 }}>{success}</div>
      )}
      {loading ? (
        <div>Loading…</div>
      ) : error ? (
        <div style={{ color: 'red' }}>{error}</div>
      ) : (
        <ul>
          {items.map((i) => (
            <li key={i.id}>
              <strong>{i.name}</strong> — {i.description} <em>({i.created_at})</em>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
