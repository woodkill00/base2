import React from 'react';

type Tab = { id: string; label: string };

type Props = {
  tabs: Tab[];
  activeTab: string;
  onChange: (_id: string) => void;
  className?: string;
};

export const GlassTabs: React.FC<Props> = ({ tabs, activeTab, onChange, className }) => {
  const onKey = (e: React.KeyboardEvent<HTMLButtonElement>, idx: number) => {
    if (e.key === 'ArrowRight') {
      const next = tabs[Math.min(tabs.length - 1, idx + 1)].id;
      onChange(next);
    } else if (e.key === 'ArrowLeft') {
      const prev = tabs[Math.max(0, idx - 1)].id;
      onChange(prev);
    }
  };

  return (
    <div className={['glass', 'glass-tabs', className].filter(Boolean).join(' ')} role="tablist">
      {tabs.map((t, i) => (
        <button
          key={t.id}
          role="tab"
          aria-selected={t.id === activeTab}
          className="glass-tab"
          onClick={() => onChange(t.id)}
          onKeyDown={(e) => onKey(e, i)}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
};

export default GlassTabs;
