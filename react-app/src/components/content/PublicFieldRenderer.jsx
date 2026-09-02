const TEXT_KINDS = new Set(['short_text', 'long_text', 'slug', 'email']);
const NUMBER_KINDS = new Set(['integer', 'decimal']);

const safeUrl = (value) => {
  try {
    const parsed = new URL(String(value));
    return ['https:', 'http:'].includes(parsed.protocol) ? parsed.href : '';
  } catch {
    return '';
  }
};

const RichText = ({ value }) => {
  if (!value || typeof value !== 'object') return null;
  if (value.type === 'text') return <>{String(value.text || '')}</>;
  const children = Array.isArray(value.children) ? value.children.slice(0, 256) : [];
  if (value.type === 'link') {
    const href = safeUrl(value.href);
    return href ? (
      <a href={href} rel="noopener noreferrer">
        {children.map((child, index) => (
          <RichText key={index} value={child} />
        ))}
      </a>
    ) : null;
  }
  const content = children.map((child, index) => <RichText key={index} value={child} />);
  if (value.type === 'heading') return <h3>{content}</h3>;
  if (value.type === 'paragraph') return <p>{content}</p>;
  if (value.type === 'blockquote') return <blockquote>{content}</blockquote>;
  if (value.type === 'code_block')
    return (
      <pre>
        <code>{content}</code>
      </pre>
    );
  if (value.type === 'list') return <ul>{content}</ul>;
  if (value.type === 'list_item') return <li>{content}</li>;
  if (value.type === 'hard_break') return <br />;
  return <>{content}</>;
};

export default function PublicFieldRenderer({ field, value }) {
  if (value === null || value === undefined || value === '') return null;
  const kind = field?.fieldKind;
  if (TEXT_KINDS.has(kind)) return <span>{String(value)}</span>;
  if (NUMBER_KINDS.has(kind)) return <span>{String(value)}</span>;
  if (kind === 'boolean') return <span>{value === true ? 'Yes' : 'No'}</span>;
  if (kind === 'date' || kind === 'datetime')
    return <time dateTime={String(value)}>{String(value)}</time>;
  if (kind === 'url') {
    const href = safeUrl(value);
    return href ? (
      <a href={href} rel="noopener noreferrer">
        {href}
      </a>
    ) : (
      <span>Unavailable link</span>
    );
  }
  if (kind === 'rich_text') return <RichText value={value} />;
  if (kind === 'enum') return <span>{String(value)}</span>;
  if (kind === 'location' && typeof value === 'object')
    return (
      <address>{[value.locality, value.region, value.country].filter(Boolean).join(', ')}</address>
    );
  if (kind === 'image' && typeof value === 'object')
    return (
      <span role="img" aria-label={String(value.altText || 'Published image')}>
        Image available
      </span>
    );
  if (kind === 'file' && typeof value === 'object')
    return <span>{String(value.label || 'Published file')}</span>;
  if (
    (kind === 'reference' || kind === 'references') &&
    (typeof value === 'string' || Array.isArray(value))
  )
    return (
      <span>{Array.isArray(value) ? `${value.length} related records` : 'Related record'}</span>
    );
  if (kind === 'json_object') return <span>Structured information</span>;
  return null;
}

export function PublicWorkspaceFields({ item }) {
  const fields = Array.isArray(item?.metadata?.workspaceFields)
    ? item.metadata.workspaceFields
    : [];
  const values = item?.metadata?.workspaceValues;
  if (!values || typeof values !== 'object' || Array.isArray(values) || !fields.length) return null;
  return (
    <dl className="workspace-public-fields">
      {fields.slice(0, 64).map((field) => (
        <div key={field.fieldKey}>
          <dt>{field.label}</dt>
          <dd>
            <PublicFieldRenderer field={field} value={values[field.fieldKey]} />
          </dd>
        </div>
      ))}
    </dl>
  );
}
