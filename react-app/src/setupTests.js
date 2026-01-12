// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';
import 'jest-axe/extend-expect';
// Polyfills for Node test environment (required by MSW/interceptors)
try {
  const { TextEncoder, TextDecoder } = require('util');
  if (typeof global.TextEncoder === 'undefined') {
    global.TextEncoder = TextEncoder;
  }
  if (typeof global.TextDecoder === 'undefined') {
    global.TextDecoder = TextDecoder;
  }
} catch (e) {
  // noop polyfill fallback
}
let server;
try {
  // Load MSW server after polyfills are applied
  // eslint-disable-next-line global-require
  server = require('./test/msw/server').server;
} catch (e) {
  // noop if MSW fails to load
}

// Start MSW before all tests, reset after each, and close after all
if (server) {
  beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }));
  afterEach(() => server.resetHandlers());
  afterAll(() => server.close());
}

// Mock environment variables
const websiteDomain = process.env.WEBSITE_DOMAIN || 'localhost';
process.env.REACT_APP_API_URL = process.env.REACT_APP_API_URL || `https://${websiteDomain}/api`;
process.env.REACT_APP_GOOGLE_CLIENT_ID = 'test-google-client-id';

// Mock window.matchMedia (needed for some components)
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {}, // deprecated
    removeListener: () => {}, // deprecated
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});

// Mock localStorage
const localStorageStore = new Map();
const getItemImpl = (key) => {
  const normalizedKey = String(key);
  return localStorageStore.has(normalizedKey) ? localStorageStore.get(normalizedKey) : null;
};
const setItemImpl = (key, value) => {
  localStorageStore.set(String(key), String(value));
};
const removeItemImpl = (key) => {
  localStorageStore.delete(String(key));
};
const clearImpl = () => {
  localStorageStore.clear();
};

const localStorageMock = {
  getItem: jest.fn(getItemImpl),
  setItem: jest.fn(setItemImpl),
  removeItem: jest.fn(removeItemImpl),
  clear: jest.fn(clearImpl),
};
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
  writable: true,
});
global.localStorage = window.localStorage;

// CRA/Jest runs with resetMocks enabled, which clears mock implementations
// before each test. Re-apply implementations so localStorage behaves like
// the real thing while still allowing call assertions.
beforeEach(() => {
  localStorageMock.getItem.mockImplementation(getItemImpl);
  localStorageMock.setItem.mockImplementation(setItemImpl);
  localStorageMock.removeItem.mockImplementation(removeItemImpl);
  localStorageMock.clear.mockImplementation(clearImpl);
});

// Suppress console errors in tests (optional)
// global.console = {
//   ...console,
//   error: jest.fn(),
//   warn: jest.fn(),
// };

// Suppress React Router v7 future flag deprecation warnings in tests only
(() => {
  const originalWarn = console.warn.bind(console);
  const shouldFilter = (args) => {
    try {
      const first = args && args[0];
      if (typeof first !== 'string') return false;
      return first.includes('React Router Future Flag Warning');
    } catch (_) {
      return false;
    }
  };
  jest.spyOn(console, 'warn').mockImplementation((...args) => {
    if (shouldFilter(args)) return;
    originalWarn(...args);
  });
})();
