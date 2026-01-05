import React from 'react';

type Props = {
  width: number;
  height: number;
  rounded?: boolean;
  className?: string;
};

export const GlassSkeleton: React.FC<Props> = ({ width, height, rounded, className }) => {
  const style = { width, height } as React.CSSProperties;
  return (
    <div
      data-testid="glass-skeleton"
      className={['glass-skeleton', rounded ? 'glass-skeleton-rounded' : '', className].filter(Boolean).join(' ')}
      style={style}
      aria-hidden="true"
    />
  );
};

export default GlassSkeleton;
