import { useEffect, useMemo, useState } from 'react';

import { useAuth } from '../contexts/AuthContext';
import AppShell from '../components/glass/AppShell';
import Navigation from '../components/Navigation';
import GlassCard from '../components/glass/GlassCard';
import GlassButton from '../components/glass/GlassButton';

const UserSettings = () => {
  const { user, updateUser } = useAuth();
  const [isEditing, setIsEditing] = useState(false);
  const initial = useMemo(
    () => ({
      name: user?.name || '',
      email: user?.email || '',
      bio: user?.bio || '',
      location: user?.location || '',
      website: user?.website || '',
    }),
    [user]
  );
  const [formData, setFormData] = useState(initial);

  useEffect(() => {
    setFormData(initial);
  }, [initial]);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    updateUser(formData);
    setIsEditing(false);
  };

  const handleCancel = () => {
    setFormData(initial);
    setIsEditing(false);
  };

  const inputClass =
    'w-full backdrop-blur-2xl bg-white/25 dark:bg-black/40 border border-white/30 dark:border-white/20 ' +
    'rounded-[var(--radius-lg)] px-4 py-3 text-foreground placeholder:text-foreground/50 dark:placeholder:text-foreground/40 ' +
    'focus:outline-none focus:ring-2 focus:ring-white/40 dark:focus:ring-white/30 focus:border-white/50 dark:focus:border-white/30 ' +
    'shadow-[0_4px_16px_0_rgba(31,38,135,0.1)] dark:shadow-[0_4px_16px_0_rgba(0,0,0,0.3)] transition-all duration-300 ease-out';

  return (
    <AppShell headerTitle="User Settings">
      <div className="mx-auto max-w-3xl px-4 py-8 space-y-6">
        <Navigation />

        <header className="space-y-1">
          <h1 className="text-xl font-semibold tracking-tight">User Settings</h1>
          <p className="text-sm opacity-80">Manage your account settings and preferences</p>
        </header>

        <GlassCard>
          <div className="p-6 space-y-6">
            <div className="flex items-center gap-4">
              <img
                src={user?.picture || 'https://via.placeholder.com/100'}
                alt="Profile"
                className="w-16 h-16 rounded-full object-cover border border-white/30 dark:border-white/20"
              />
              <div>
                <div className="text-base font-semibold">{user?.name || ''}</div>
                <div className="text-sm opacity-80">{user?.email || ''}</div>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <label className="block text-sm font-medium" htmlFor="name">
                  Full Name
                </label>
                <input
                  id="name"
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  disabled={!isEditing}
                  className={[inputClass, !isEditing ? 'opacity-70 cursor-not-allowed' : ''].join(
                    ' '
                  )}
                />
              </div>

              <div className="space-y-2">
                <label className="block text-sm font-medium" htmlFor="email">
                  Email Address
                </label>
                <input
                  id="email"
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  disabled
                  className={[inputClass, 'opacity-70 cursor-not-allowed'].join(' ')}
                />
                <p className="text-xs opacity-70">
                  Email cannot be changed (linked to Google account)
                </p>
              </div>

              <div className="space-y-2">
                <label className="block text-sm font-medium" htmlFor="bio">
                  Bio
                </label>
                <textarea
                  id="bio"
                  name="bio"
                  value={formData.bio}
                  onChange={handleChange}
                  disabled={!isEditing}
                  rows={4}
                  placeholder="Tell us about yourself..."
                  className={[inputClass, !isEditing ? 'opacity-70 cursor-not-allowed' : ''].join(
                    ' '
                  )}
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="block text-sm font-medium" htmlFor="location">
                    Location
                  </label>
                  <input
                    id="location"
                    type="text"
                    name="location"
                    value={formData.location}
                    onChange={handleChange}
                    disabled={!isEditing}
                    placeholder="City, Country"
                    className={[inputClass, !isEditing ? 'opacity-70 cursor-not-allowed' : ''].join(
                      ' '
                    )}
                  />
                </div>

                <div className="space-y-2">
                  <label className="block text-sm font-medium" htmlFor="website">
                    Website
                  </label>
                  <input
                    id="website"
                    type="url"
                    name="website"
                    value={formData.website}
                    onChange={handleChange}
                    disabled={!isEditing}
                    placeholder="https://example.com"
                    className={[inputClass, !isEditing ? 'opacity-70 cursor-not-allowed' : ''].join(
                      ' '
                    )}
                  />
                </div>
              </div>

              <div className="flex flex-wrap justify-end gap-2">
                {!isEditing ? (
                  <GlassButton type="button" variant="secondary" onClick={() => setIsEditing(true)}>
                    Edit Profile
                  </GlassButton>
                ) : (
                  <>
                    <GlassButton type="submit" variant="primary">
                      Save Changes
                    </GlassButton>
                    <GlassButton type="button" variant="ghost" onClick={handleCancel}>
                      Cancel
                    </GlassButton>
                  </>
                )}
              </div>
            </form>

            <div className="pt-6 border-t border-white/20 dark:border-white/10 space-y-2">
              <h2 className="text-sm font-semibold tracking-tight">Danger Zone</h2>
              <p className="text-sm opacity-80">
                Once you delete your account, there is no going back. Please be certain.
              </p>
              <GlassButton type="button" variant="ghost">
                Delete Account
              </GlassButton>
            </div>
          </div>
        </GlassCard>
      </div>
    </AppShell>
  );
};
export default UserSettings;
