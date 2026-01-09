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
};

export const GlassInput: React.FC<Props> = ({ id, label, name, type, value, onChange, placeholder, error, className, ariaInvalid, ariaDescribedBy }) => {
  return (
    <div className={['glass', 'glass-input', className].filter(Boolean).join(' ')}>
      {label ? <label htmlFor={id} className="glass-input-label">{label}</label> : null}
      <input
        id={id}
        name={name}
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className="glass-input-field"
        aria-invalid={ariaInvalid}
        aria-describedby={ariaDescribedBy}
      />
      {error ? <div className="glass-input-error" role="alert">{error}</div> : null}
    </div>
  );
};

export default GlassInput;
