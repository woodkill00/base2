import React from 'react';

type Props = {
  variant?: 'primary' | 'secondary' | 'ghost';
  disabled?: boolean;
  className?: string;
  children?: React.ReactNode;
  onClick?: React.MouseEventHandler<HTMLButtonElement>;
  type?: 'button' | 'submit' | 'reset';
};

export const GlassButton: React.FC<Props> = ({ variant = 'primary', disabled, className, children, onClick, type = 'button' }) => {
  const baseStyles =
    'backdrop-blur-2xl rounded-[var(--radius-lg)] transition-all duration-300 ease-out border px-6 py-3 ' +
    'disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 ' +
    'focus-visible:ring-white/40 dark:focus-visible:ring-white/30 focus-visible:ring-offset-2 focus-visible:ring-offset-transparent';

  const variants: Record<NonNullable<Props['variant']>, string> = {
    primary:
      'bg-white/25 dark:bg-black/40 hover:bg-white/35 dark:hover:bg-black/50 border-white/40 dark:border-white/30 ' +
      'shadow-[0_4px_16px_0_rgba(31,38,135,0.15)] dark:shadow-[0_4px_16px_0_rgba(0,0,0,0.3)] dark:shadow-[0_0_20px_0_rgba(139,92,246,0.1)] ' +
      'hover:shadow-[0_6px_24px_0_rgba(31,38,135,0.2)] dark:hover:shadow-[0_6px_24px_0_rgba(0,0,0,0.4)] dark:hover:shadow-[0_0_30px_0_rgba(139,92,246,0.15)] ' +
      'hover:-translate-y-0.5',
    secondary:
      'bg-white/20 dark:bg-black/30 hover:bg-white/30 dark:hover:bg-black/40 border-white/30 dark:border-white/20 hover:-translate-y-0.5',
    ghost:
      'bg-transparent hover:bg-white/20 dark:hover:bg-black/30 border-white/30 dark:border-white/20 hover:-translate-y-0.5',
  };

  const classes = [baseStyles, variants[variant], className].filter(Boolean).join(' ');
  return (
    <button type={type} className={classes} disabled={disabled} onClick={onClick}>
      {children}
    </button>
  );
};

export default GlassButton;
