# Quickstart — React Glass UI System + App Shell

See the feature specification at specs/002-react-design/spec.md and the implementation plan at specs/002-react-design/plan.md for full context.

## Prerequisites

- Node.js (per repo README)
- React app dependencies installed: `cd react-app && npm install`

## Run the App

```bash
cd react-app
npm start
```

## Run Storybook

```bash
cd react-app
npm run storybook
```

## Verify Theming & Glass

- Toggle theme using the UI control; confirm persistence across reloads.
- Check frosted translucency, backdrop blur, border/shadow depth, hover elevation, and focus-visible glow.
- Ensure `.dark` theme is not flat or inverted.

## Accessibility Checks

- Keyboard navigation across components.
- Focus-visible shows 3px neon glow.
- Inline SVG icons include `aria-label` and `role="img"`.
- Contrast ≥ 4.5:1 for key text/controls.

## Notes

- No backend/auth or API contract changes in this feature.
- Layout sizing must use CSS `calc()` per spec.

### Theme Persistence (Cookie)

- Theme order: backend profile (authenticated) > client cookie (`theme=light|dark`) > `prefers-color-scheme` fallback.
- Cookie attributes: Secure=true, SameSite=Lax, HttpOnly=false, Path=/, Domain=.woodkilldev.com, Expires=180 days.
- Tip: To test fallback, clear the `theme` cookie and reload; to test cross-subdomain, open admin/swagger subdomains.

### Blur Fallback

- If `backdrop-filter` is unsupported, the UI uses semi-transparent backgrounds with subtle border + shadow to maintain glass fidelity (no blur emulation).
