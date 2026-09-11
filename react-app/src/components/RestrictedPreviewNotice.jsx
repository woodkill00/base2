export default function RestrictedPreviewNotice({
  mode = import.meta.env.VITE_BASE2_PREVIEW_MODE,
}) {
  if (mode !== 'restricted') return null;
  return (
    <aside
      aria-label="Preview restrictions"
      style={{
        background: '#351c0a',
        color: '#fff4e8',
        borderBottom: '2px solid #f97316',
        padding: '0.75rem 1rem',
        textAlign: 'center',
      }}
    >
      Restricted preview: uploads, media processing, and content tools are unavailable. Login,
      settings, and other non-media pages remain available for testing.
    </aside>
  );
}
