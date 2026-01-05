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
  const classes = ['glass', 'glass-interactive', 'glass-btn', `glass-btn-${variant}`, className].filter(Boolean).join(' ');
  return (
    <button type={type} className={classes} disabled={disabled} onClick={onClick}>
      {children}
    </button>
  );
};

export default GlassButton;
