export default function PasswordRequirements({ value, id = 'password-help' }) {
  const checks = [
    ['At least 8 characters', value.length >= 8],
    ['An uppercase letter', /[A-Z]/.test(value)],
    ['A lowercase letter', /[a-z]/.test(value)],
    ['A number', /[0-9]/.test(value)],
  ];
  return (
    <div id={id} className="text-sm" aria-live="polite" aria-atomic="true">
      <p>Password requirements</p>
      <ul className="mt-2 space-y-1">
        {checks.map(([label, met]) => (
          <li key={label}>
            {value ? <span>{met ? 'Met: ' : 'Needed: '}</span> : null}
            {label}
          </li>
        ))}
      </ul>
    </div>
  );
}
