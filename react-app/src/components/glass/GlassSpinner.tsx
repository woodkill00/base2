import React from 'react';

type Props = {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
};

export const GlassSpinner: React.FC<Props> = ({ size = 'md', className }) => {
  return (
    <div
      data-testid="glass-spinner"
      className={['glass-spinner', className].filter(Boolean).join(' ')}
      aria-busy="true"
      aria-live="polite"
    >
      <div className={`glass-spinner-circle glass-spinner-${size}`} />
    </div>
  );
};

export default GlassSpinner;
