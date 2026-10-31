import { validPublicContent } from '../../services/workspaceRecord';

export default function PublicContentFields({ value, onChange, disabled = false }) {
  const valid = validPublicContent(value);
  return (
    <section className="space-y-3 rounded-xl border border-white/10 p-4" aria-label="Public text">
      <p className="text-sm opacity-80">
        Only intentionally public copy belongs here. This text can appear on published,
        public-eligible pages. Private custom field values remain private. When review is not
        required, changes to an already published record may appear immediately.
      </p>
      {['excerpt', 'body'].map((key) => {
        const limit = key === 'excerpt' ? 2000 : 20000;
        const text = value?.[key];
        return (
          <div key={key} className="space-y-1">
            <label htmlFor={`public-content-${key}`} className="text-sm font-medium">
              Public {key}
            </label>
            <textarea
              id={`public-content-${key}`}
              value={typeof text === 'string' ? text : ''}
              rows={key === 'excerpt' ? 3 : 8}
              disabled={disabled}
              aria-describedby={`public-content-${key}-count`}
              className="min-h-11 w-full rounded-xl border border-white/20 bg-slate-950/80 px-3 py-2"
              onChange={(event) => onChange({ ...value, [key]: event.target.value })}
            />
            <p id={`public-content-${key}-count`} className="text-xs opacity-65">
              {typeof text === 'string' ? Array.from(text).length : 0} / {limit} Unicode characters.
              Plain text; HTML is displayed literally.
            </p>
          </div>
        );
      })}
      {!valid && (
        <p role="alert">
          Public text must contain valid Unicode without NUL and stay within the character limits.
        </p>
      )}
    </section>
  );
}
