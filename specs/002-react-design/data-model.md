# Data Model — React Glass UI System + App Shell

## Entities

### ThemePreference

- Fields: `value: 'light' | 'dark'`, `persisted: boolean`
- Relationships: N/A (frontend-only)
- Validation: value must be one of `light` or `dark`.
- State transitions: toggle between light/dark; apply `.dark` class accordingly.

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

## Layout Tokens (CSS calc)

- Root height: `calc(100vh - env(safe-area-inset-top) - env(safe-area-inset-bottom))`
- Sidebar width: `calc(100vw * 0.25)` (min 320px, max 400px)
- Header height: `calc(100vh * 0.08)` (min 64px)
- Footer height: `calc(100vh * 0.08)` (min 56px)
- Content height: `calc(100vh - header - footer)`
