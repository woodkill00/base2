# Quickstart — React Glass UI System + App Shell

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
