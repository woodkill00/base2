import React from 'react';

type Props = {
  variant?: 'default' | 'elevated' | 'subtle';
  interactive?: boolean;
  hover?: boolean;
  className?: string;
  style?: React.CSSProperties;
  children?: React.ReactNode;
};

export const GlassCard: React.FC<Props> = ({
  variant = 'default',
  interactive,
  hover,
  className,
  style,
  children,
}) => {
  const base =
    'backdrop-blur-2xl border rounded-[var(--radius-lg)] transition-all duration-300 ease-out ' +
    'shadow-[0_8px_32px_0_rgba(31,38,135,0.15)] dark:shadow-[0_8px_32px_0_rgba(0,0,0,0.4)] dark:shadow-[0_0_40px_0_rgba(139,92,246,0.1)]';

  const variantStyles: Record<NonNullable<Props['variant']>, string> = {
    default: 'bg-white/25 dark:bg-black/40 border-white/30 dark:border-white/20',
    elevated: 'bg-white/25 dark:bg-black/40 border-white/30 dark:border-white/20',
    subtle: 'bg-white/20 dark:bg-black/30 border-white/30 dark:border-white/20',
  };

  const hoverStyles =
    'hover:bg-white/35 dark:hover:bg-black/50 hover:shadow-[0_12px_48px_0_rgba(31,38,135,0.2)] ' +
    'dark:hover:shadow-[0_12px_48px_0_rgba(0,0,0,0.5)] dark:hover:shadow-[0_0_50px_0_rgba(139,92,246,0.15)] hover:-translate-y-1';

  const classes = [base, variantStyles[variant], interactive || hover ? hoverStyles : '', className]
    .filter(Boolean)
    .join(' ');
  return (
    <div data-testid="glass-card" className={classes} style={style}>
      {children}
    </div>
  );
};

export default GlassCard;
