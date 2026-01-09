import React from 'react';

type Props = {
  items?: string[];
};

const defaultItems = ['Home', 'Dashboard', 'Settings', 'Users', 'Help'];

export const GlassSidebar: React.FC<Props> = ({ items = defaultItems }) => {
  return (
    <aside
      className="glass glass-sidebar"
      style={{ width: 'var(--sidebar-w)', minWidth: '320px', maxWidth: '400px' }}
      aria-label="Sidebar"
    >
      <ul className="glass-sidebar-list">
        {items.map((i) => (
          <li key={i} className="glass-sidebar-item">{i}</li>
        ))}
      </ul>
    </aside>
  );
};

export default GlassSidebar;
