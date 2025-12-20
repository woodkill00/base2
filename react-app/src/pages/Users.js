import React, { useEffect, useState } from 'react';
import { usersAPI } from '../services/users';

const Users = () => {
  const [users, setUsers] = useState([]);
  const [me, setMe] = useState(null);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');

  const load = async () => {
    try {
      const list = await usersAPI.list();
      setUsers(list.users || []);
      const meData = await usersAPI.me();
      setMe(meData.user || null);
    } catch (e) {
      console.error('load users failed', e);
    }
  };

  useEffect(() => { load(); }, []);

  const doLogin = async (e) => {
    e.preventDefault();
    setMessage('');
    try {
      const res = await usersAPI.login(email, password);
      if (res.success) {
        setMessage('Logged in');
        setEmail('');
        setPassword('');
        load();
      } else {
        setMessage(res.error || 'Login failed');
      }
    } catch (err) {
      setMessage('Login failed');
    }
  };

  const doLogout = async () => {
    setMessage('');
    try {
      const res = await usersAPI.logout();
      if (res.success) {
        setMessage('Logged out');
        load();
      }
    } catch (err) {
      setMessage('Logout failed');
    }
  };

  return (
    <div style={{ padding: 20 }}>
      <h2>Users</h2>
      {message && <p>{message}</p>}

      <div style={{ display: 'flex', gap: 40 }}>
        <div>
          <h3>Current User</h3>
          {me ? (
            <div>
              <div><b>ID:</b> {me.id}</div>
              <div><b>Username:</b> {me.username}</div>
              <div><b>Email:</b> {me.email}</div>
              <button onClick={doLogout}>Logout</button>
            </div>
          ) : (
            <div>Not authenticated</div>
          )}

          <h3 style={{ marginTop: 20 }}>Login</h3>
          <form onSubmit={doLogin}>
            <div>
              <label>Email</label><br />
              <input value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div>
              <label>Password</label><br />
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
            </div>
            <button type="submit">Login</button>
          </form>
        </div>

        <div>
          <h3>All Users</h3>
          <ul>
            {(users || []).map(u => (
              <li key={u.id}>
                {u.username || 'user'} — {u.email} {u.is_staff ? '(staff)' : ''}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
};

export default Users;
