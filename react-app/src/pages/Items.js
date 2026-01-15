import { useEffect, useState } from 'react';
import { itemsAPI } from '../services/items';
import AppShell from '../components/glass/AppShell';
import GlassCard from '../components/glass/GlassCard';
import GlassButton from '../components/glass/GlassButton';
import GlassInput from '../components/glass/GlassInput';

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
    <AppShell headerTitle="Items">
      <div style={{ maxWidth: 900, margin: '0 auto', padding: 20 }}>
        <GlassCard>
          <h1 style={{ marginTop: 0 }}>Items</h1>
          <p>Backed by Django models, served via FastAPI.</p>

          <form onSubmit={onCreate} style={{ display: 'grid', gap: 12, marginBottom: 16 }}>
            <div style={{ display: 'grid', gap: 12, gridTemplateColumns: '1fr 2fr' }}>
              <GlassInput
                id="item-name"
                name="name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Name"
                ariaInvalid={error && error.toLowerCase().includes('name') ? 'true' : 'false'}
              />
              <GlassInput
                id="item-description"
                name="description"
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Description"
                ariaInvalid={error ? 'true' : 'false'}
              />
            </div>

            <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
              <GlassButton type="submit" variant="primary">
                Add
              </GlassButton>
              {success ? <div style={{ margin: 0 }}>{success}</div> : null}
              {error ? (
                <div role="alert" style={{ margin: 0 }}>
                  {error}
                </div>
              ) : null}
            </div>
          </form>

          {loading ? (
            <div>Loading…</div>
          ) : (
            <ul>
              {items.map((i) => (
                <li key={i.id}>
                  <strong>{i.name}</strong> — {i.description} <em>({i.created_at})</em>
                </li>
              ))}
            </ul>
          )}
        </GlassCard>
      </div>
    </AppShell>
  );
}
