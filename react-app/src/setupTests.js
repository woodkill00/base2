// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';

// CRA/Jest can struggle with some ESM-only node_modules (e.g., axios). We don't need
// real HTTP in unit tests, so use a manual mock.
jest.mock('axios');

// Mock environment variables
const websiteDomain = process.env.WEBSITE_DOMAIN || 'localhost';
process.env.REACT_APP_API_URL =
  process.env.REACT_APP_API_URL || `https://${websiteDomain}/api`;
process.env.REACT_APP_GOOGLE_CLIENT_ID = 'test-google-client-id';

// Mock window.matchMedia (needed for some components)
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
  writable: true,
});
global.localStorage = window.localStorage;

// Suppress console errors in tests (optional)
// global.console = {
//   ...console,
//   error: jest.fn(),
//   warn: jest.fn(),
// };
