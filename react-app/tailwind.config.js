/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: ['./public/index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      spacing: {
        section: 'var(--space)',
      },
      borderRadius: {
        glass: 'var(--radius)',
      },
      colors: {
        primaryBgDark: '#0f0f23',
        cardDark: '#1a1a2e',
        accentBlue: '#1e90ff',
        primaryBgLight: '#f8fafc',
        textLight: '#1e293b',
      },
      boxShadow: {
        glass: 'inset 0 1px 0 rgba(255,255,255,0.2), 0 8px 32px rgba(0,0,0,0.35)',
      },
      backdropBlur: {
        glass: '20px',
      },
    },
  },
  plugins: [
    function ({ addUtilities }) {
      const newUtilities = {
        '.glass': {
          backdropFilter: 'blur(20px)',
          background: 'rgba(255,255,255,0.1)',
          border: '1px solid rgba(255,255,255,0.2)',
        },
        '.glass-strong': {
          backdropFilter: 'blur(24px)',
          background: 'rgba(15,15,35,0.4)',
          border: '1px solid rgba(255,255,255,0.3)',
        },
        '.glass-pill': {
          backdropFilter: 'blur(20px)',
          background: 'rgba(255,255,255,0.12)',
          border: '1px solid rgba(255,255,255,0.25)',
          borderRadius: '9999px',
        },
      };
      addUtilities(newUtilities, ['responsive', 'hover', 'focus']);

      // Preserve the approved v3 sibling-margin semantics. v4's default
      // last-child/bottom-margin implementation collapses differently around
      // existing cards. Static utilities take precedence over the built-in
      // functional utility; no component or screenshot changes are needed.
      const legacySpacing = {};
      for (let step = 0; step <= 96; step += 1) {
        const name = String(step);
        const value = `${step / 4}rem`;
        legacySpacing[`.space-y-${name}`] = {
          '& > :not([hidden]) ~ :not([hidden])': {
            '--tw-space-y-reverse': '0',
            marginTop: `calc(${value} * calc(1 - var(--tw-space-y-reverse)))`,
            marginBottom: `calc(${value} * var(--tw-space-y-reverse))`,
          },
        };
        legacySpacing[`.space-x-${name}`] = {
          '& > :not([hidden]) ~ :not([hidden])': {
            '--tw-space-x-reverse': '0',
            marginRight: `calc(${value} * var(--tw-space-x-reverse))`,
            marginLeft: `calc(${value} * calc(1 - var(--tw-space-x-reverse)))`,
          },
        };
      }
      legacySpacing['.space-y-reverse'] = {
        '& > :not([hidden]) ~ :not([hidden])': { '--tw-space-y-reverse': '1' },
      };
      legacySpacing['.space-x-reverse'] = {
        '& > :not([hidden]) ~ :not([hidden])': { '--tw-space-x-reverse': '1' },
      };
      addUtilities(legacySpacing);
    },
  ],
};
