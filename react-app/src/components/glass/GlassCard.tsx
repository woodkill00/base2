import React from 'react';

type Props = {
  variant?: 'default' | 'elevated' | 'subtle';
  interactive?: boolean;
  className?: string;
  children?: React.ReactNode;
};

export const GlassCard: React.FC<Props> = ({ variant = 'default', interactive, className, children }) => {
  const classes = ['glass', 'glass-card', interactive ? 'glass-interactive' : '', `glass-card-${variant}`, className]
    .filter(Boolean)
    .join(' ');
  return (
    <div data-testid="glass-card" className={classes}>
      {children}
    </div>
  );
};

export default GlassCard;
