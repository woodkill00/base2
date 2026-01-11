# Data Model — React Glass UI System + App Shell

## Entities

### ThemePreference

- Fields: `value: 'light' | 'dark'`, `persisted: boolean`
- Relationships: N/A (frontend-only)
- Validation: value must be one of `light` or `dark`.
- State transitions: toggle between light/dark; apply `.dark` class accordingly.

### HomePage (composition)

- Sections: `hero`, `features`, `visual`, `trust`, `footer`
- Relationships: composed of glass components (cards, buttons, input, icons)
- Validation: renders without API calls; accessible labels on SVGs; keyboard navigation across interactive elements
- State transitions: animations respect `prefers-reduced-motion`; hover/focus states per glass tokens

## Component Contracts

### GlassButton

- Props: `variant: 'primary' | 'secondary' | 'ghost'`, `disabled?: boolean`, `className?: string`, `aria-* passthrough`
- Behavior: hover elevation; focus-visible glow; disabled state styling.

### GlassCard

- Props: `variant?: 'default' | 'elevated' | 'subtle'`, `interactive?: boolean`, `className?: string`, `aria-* passthrough`
- Behavior: frosted translucency; backdrop blur; optional interactive elevation.

### GlassInput

- Props: `value`, `onChange`, `placeholder?`, `error?`, `className?`, `aria-* passthrough`
- Behavior: accessible label; focus glow; error state styling.

### GlassTabs

- Props: `tabs: Array<{ id: string; label: string }>` , `activeTab: string`, `onChange(id: string)`, `className?`
- Behavior: keyboard navigation; focus management; calc-based layout widths.

### GlassModal

- Props: `open: boolean`, `onClose: () => void`, `className?`, `aria-*`
- Behavior: ESC + backdrop click close; focus trap; return focus to trigger.

### GlassSpinner

- Props: `size?: 'sm' | 'md' | 'lg'`, `className?`
- Behavior: transform-only animation; reduced-motion respects user preference.

### GlassSkeleton

- Props: `width`, `height`, `rounded?`, `className?`
- Behavior: shimmer effect with reduced-motion fallback.

### HomeHero

- Props: `title`, `subtitle`, `primaryCta`, `secondaryCta?`, `showInput?`
- Behavior: centered `GlassCard` with clamp-based typography; idle float; hover elevation; CTA pulse; optional decorative/interactive input

### HomeFeatures

- Props: `items: Array<{ icon: SVG; title: string; description: string }>`
- Behavior: responsive grid `repeat(auto-fit, minmax(calc(300px - 2rem), 1fr))`; hover lift; icon glow; keyboard focusable

### HomeVisual

- Props: `src: string (SVG/WebP)`, `alt: string`
- Behavior: lazy-loaded illustration inside glass frame; minor overflow allowed for depth; no layout dependency

### HomeTrust

- Props: `items: Array<{ icon?: SVG; text: string }>`
- Behavior: small glass pills/cards; keyboard focusable; contrast ≥ 4.5:1

### HomeFooter

- Props: `links: Array<{ label: string; href: string }>`
- Behavior: glass container; SVG social icons; secondary text styling

## Layout Tokens (CSS calc)

- Root height: `calc(100vh - env(safe-area-inset-top) - env(safe-area-inset-bottom))`
- Sidebar width: `calc(100vw * 0.25)` (min 320px, max 400px)
- Header height: `calc(100vh * 0.08)` (min 64px)
- Footer height: `calc(100vh * 0.08)` (min 56px)
- Content height: `calc(100vh - header - footer)`

### Public Home Page Tokens

- Hero width: `min(calc(100% - 4rem), 960px)`
- Hero min-height: `calc(100vh * 0.5)`
- Grid: `repeat(auto-fit, minmax(calc(300px - 2rem), 1fr))`
