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
      <div className="mx-auto max-w-3xl px-4 py-8">
        <GlassCard>
          <div className="p-6 space-y-6">
            <header className="space-y-1">
              <h1 className="text-xl font-semibold tracking-tight">Items</h1>
              <p className="text-sm opacity-80">Backed by Django models, served via FastAPI.</p>
            </header>

            <form onSubmit={onCreate} className="space-y-4">
              <div className="grid gap-3 md:grid-cols-3">
                <div className="md:col-span-1">
                  <GlassInput
                    id="item-name"
                    name="name"
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Name"
                    ariaInvalid={error && error.toLowerCase().includes('name') ? 'true' : 'false'}
                  />
                </div>
                <div className="md:col-span-2">
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
              </div>

              <div className="flex flex-wrap gap-3 items-center">
                <GlassButton type="submit" variant="primary">
                  Add
                </GlassButton>
                {success ? <div className="text-sm">{success}</div> : null}
                {error ? (
                  <div role="alert" className="text-sm">
                    {error}
                  </div>
                ) : null}
              </div>
            </form>

            {loading ? (
              <div className="text-sm">Loading…</div>
            ) : (
              <ul className="space-y-2">
                {items.map((i) => (
                  <li key={i.id} className="text-sm">
                    <strong>{i.name}</strong> — {i.description} <em>({i.created_at})</em>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </GlassCard>
      </div>
    </AppShell>
  );
}
