import React, { useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';
import './password-control.css';

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
  inputMode?: React.HTMLAttributes<HTMLInputElement>['inputMode'];
  autoComplete?: string;
  disabled?: boolean;
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
  inputMode,
  autoComplete,
  disabled = false,
}) => {
  const [revealed, setRevealed] = useState(false);
  const [capsLock, setCapsLock] = useState(false);
  const password = type === 'password';
  const visible = password && revealed && !disabled;
  return (
    <div className={['w-full', className].filter(Boolean).join(' ')}>
      {label ? (
        <label htmlFor={id} className="block text-sm font-medium mb-2">
          {label}
        </label>
      ) : null}
      <div
        className={`relative w-full ${password ? 'volcano-password-control' : ''}`}
        onBlur={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
            setRevealed(false);
            setCapsLock(false);
          }
        }}
      >
        {icon ? (
          <div className="absolute left-4 top-1/2 -translate-y-1/2 text-foreground/60 dark:text-foreground/50 pointer-events-none">
            {icon}
          </div>
        ) : null}
        <input
          id={id}
          name={name}
          type={visible ? 'text' : type}
          disabled={disabled}
          value={value}
          onChange={onChange}
          onKeyDown={(event) => password && setCapsLock(event.getModifierState('CapsLock'))}
          onKeyUp={(event) => password && setCapsLock(event.getModifierState('CapsLock'))}
          placeholder={placeholder}
          className={
            'base2-input w-full backdrop-blur-2xl bg-white/25 dark:bg-black/40 ' +
            'border border-white/30 dark:border-white/20 rounded-[var(--radius-lg)] ' +
            `px-4 py-3 ${icon ? 'pl-12' : ''} ` +
            'text-foreground placeholder:text-foreground/50 dark:placeholder:text-foreground/40 ' +
            'focus:outline-none focus:ring-2 focus:ring-white/40 dark:focus:ring-white/30 ' +
            'focus:border-white/50 dark:focus:border-white/30 ' +
            'shadow-[0_4px_16px_0_rgba(31,38,135,0.1)] dark:shadow-[0_4px_16px_0_rgba(0,0,0,0.3)] ' +
            'transition-all duration-300 ease-out'
          }
          aria-invalid={ariaInvalid}
          aria-describedby={
            [ariaDescribedBy, password && capsLock ? `${id}-caps-lock` : null]
              .filter(Boolean)
              .join(' ') || undefined
          }
          inputMode={inputMode}
          autoComplete={autoComplete}
        />
        {password ? (
          <button
            type="button"
            className="volcano-password-toggle"
            aria-label={visible ? 'Hide password' : 'Show password'}
            aria-pressed={visible}
            aria-controls={id}
            disabled={disabled}
            onPointerDown={(event) => event.preventDefault()}
            onClick={() => setRevealed((current) => !current)}
          >
            {visible ? (
              <EyeOff size={20} aria-hidden="true" />
            ) : (
              <Eye size={20} aria-hidden="true" />
            )}
          </button>
        ) : null}
      </div>
      {password && capsLock ? (
        <p id={`${id}-caps-lock`} role="status" className="mt-2 text-sm">
          Caps Lock is on.
        </p>
      ) : null}
      {error ? (
        <div className="text-sm mt-2" role="alert">
          {error}
        </div>
      ) : null}
    </div>
  );
};

export default GlassInput;
