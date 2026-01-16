import React from 'react';

type Props = {
  id: string;
  label?: string;
  name?: string;
  type?: string;
  value: string;
  onChange: React.ChangeEventHandler<HTMLInputElement>;
  placeholder?: string;
  error?: string;
  className?: string;
  ariaInvalid?: 'true' | 'false';
  ariaDescribedBy?: string;
  icon?: React.ReactNode;
};

export const GlassInput: React.FC<Props> = ({
  id,
  label,
  name,
  type,
  value,
  onChange,
  placeholder,
  error,
  className,
  ariaInvalid,
  ariaDescribedBy,
  icon,
}) => {
  return (
    <div className={['w-full', className].filter(Boolean).join(' ')}>
      {label ? (
        <label htmlFor={id} className="block text-sm font-medium mb-2">
          {label}
        </label>
      ) : null}
      <div className="relative w-full">
        {icon ? (
          <div className="absolute left-4 top-1/2 -translate-y-1/2 text-foreground/60 dark:text-foreground/50 pointer-events-none">
            {icon}
          </div>
        ) : null}
        <input
          id={id}
          name={name}
          type={type}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          className={
            'w-full backdrop-blur-2xl bg-white/25 dark:bg-black/40 ' +
            'border border-white/30 dark:border-white/20 rounded-[var(--radius-lg)] ' +
            `px-4 py-3 ${icon ? 'pl-12' : ''} ` +
            'text-foreground placeholder:text-foreground/50 dark:placeholder:text-foreground/40 ' +
            'focus:outline-none focus:ring-2 focus:ring-white/40 dark:focus:ring-white/30 ' +
            'focus:border-white/50 dark:focus:border-white/30 ' +
            'shadow-[0_4px_16px_0_rgba(31,38,135,0.1)] dark:shadow-[0_4px_16px_0_rgba(0,0,0,0.3)] ' +
            'transition-all duration-300 ease-out'
          }
          aria-invalid={ariaInvalid}
          aria-describedby={ariaDescribedBy}
        />
      </div>
      {error ? (
        <div className="text-sm mt-2" role="alert">
          {error}
        </div>
      ) : null}
    </div>
  );
};

export default GlassInput;
