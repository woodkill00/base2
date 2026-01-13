/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './public/index.html',
    './src/**/*.{js,jsx,ts,tsx}'
  ],
  theme: {
    extend: {
      spacing: {
        section: 'var(--space)'
      },
      borderRadius: {
        glass: 'var(--radius)'
      },
      colors: {
        primaryBgDark: '#0f0f23',
        cardDark: '#1a1a2e',
        accentBlue: '#1e90ff',
        primaryBgLight: '#f8fafc',
        textLight: '#1e293b'
      },
      boxShadow: {
        'glass': 'inset 0 1px 0 rgba(255,255,255,0.2), 0 8px 32px rgba(0,0,0,0.35)'
      },
      backdropBlur: {
        'glass': '20px'
      }
    }
  },
  plugins: [
    function({ addUtilities }) {
      const newUtilities = {
        '.glass': {
          backdropFilter: 'blur(20px)',
          background: 'rgba(255,255,255,0.1)',
          border: '1px solid rgba(255,255,255,0.2)'
        },
        '.glass-strong': {
          backdropFilter: 'blur(24px)',
          background: 'rgba(15,15,35,0.4)',
          border: '1px solid rgba(255,255,255,0.3)'
        },
        '.glass-pill': {
          backdropFilter: 'blur(20px)',
          background: 'rgba(255,255,255,0.12)',
          border: '1px solid rgba(255,255,255,0.25)',
          borderRadius: '9999px'
        }
      };
      addUtilities(newUtilities, ['responsive', 'hover', 'focus']);
    }
  ]
};
