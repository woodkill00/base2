# Design Port Map (junk/idea → base2 react-app)

This file documents how the reference design system under `./junk/idea/` maps into the production React app under `./react-app/`.

## Source inputs (reference)

Styles:

- `junk/idea/src/styles/index.css` (import order)
- `junk/idea/src/styles/theme.css` (design tokens)
- `junk/idea/src/styles/glass.css` (gradient background + scrolling + scrollbar)

Components (layout/content intent):

- `junk/idea/src/app/components/header.tsx`
- `junk/idea/src/app/components/side-menu.tsx`
- `junk/idea/src/app/components/hero.tsx`
- `junk/idea/src/app/components/features.tsx`
- `junk/idea/src/app/components/trust-section.tsx`
- `junk/idea/src/app/components/footer.tsx`

## Base2 targets

### Global style import order

Reference order:

- fonts → tailwind → theme → glass (see `junk/idea/src/styles/index.css`)

Base2 order (see `react-app/src/App.css`):

- tokens → background → glass → app/global styles

### Token mapping

`junk/idea/src/styles/theme.css` is Tailwind-oriented and uses OKLCH variables. Base2 uses a smaller, app-specific set of CSS custom properties.

| Intent               | Reference (junk/idea)                          | Base2 (react-app)                                  |
| -------------------- | ---------------------------------------------- | -------------------------------------------------- |
| Theme surface colors | `--background`, `--foreground`, `--card`, etc. | `--glass-bg-*`, `--glass-border`, `--glass-shadow` |
| Focus ring / outline | `--ring` and Tailwind `outline-ring`           | `--focus-glow` (3px neon ring)                     |
| Sidebar sizing       | `--sidebar*` (semantic colors)                 | `--sidebar-w` (layout token)                       |
| Drawer sizing        | N/A (component-driven)                         | `--drawer-w`                                       |
| Header/footer sizing | Typography/base styles                         | `--header-h`, `--footer-h`, `--content-h`          |

### Background system

Reference background lives in `junk/idea/src/styles/glass.css` via `.gradient-background`.

Base2 ports that into:

- `react-app/src/styles/background.css` (`.gradient-background`, light/dark variants, reduced-motion guards)

### Drawer/sidebar transitions

Reference behavior is implemented in:

- `junk/idea/src/app/components/side-menu.tsx`

Base2 implements the required primitives via:

- CSS: `react-app/src/styles/glass.css` (`.glass-drawer-*` primitives)
- Components/tests: `react-app/src/components/glass/GlassSidebar.tsx` + tests
