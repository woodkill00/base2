export const parameters = {
  actions: { argTypesRegex: "^on[A-Z].*" },
  controls: {
    matchers: {
      color: /(background|color)$/i,
      date: /Date$/,
    },
  },
};

// Global styles for stories (glass tokens + base styles)
import '../src/styles/tokens.css';
import '../src/styles/glass.css';

// Global toolbar controls
export const globalTypes = {
  theme: {
    name: 'Theme',
    description: 'Global theme for components',
    defaultValue: 'light',
    toolbar: {
      icon: 'circlehollow',
      items: ['light', 'dark'],
    },
  },
  backdrop: {
    name: 'Backdrop',
    description: 'Glass backdrop rendering',
    defaultValue: 'blur',
    toolbar: {
      icon: 'contrast',
      items: [
        { value: 'blur', title: 'Blur' },
        { value: 'fallback', title: 'Fallback' },
      ],
    },
  },
};

// Decorator to apply theme/backdrop globals
export const decorators = [
  (Story, context) => {
    const root = document.documentElement;
    root.classList.remove('dark');
    root.classList.remove('no-backdrop');
    if (context.globals.theme === 'dark') {
      root.classList.add('dark');
    }
    if (context.globals.backdrop === 'fallback') {
      root.classList.add('no-backdrop');
    }
    return Story();
  },
];