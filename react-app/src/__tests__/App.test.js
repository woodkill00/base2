import { render } from '@testing-library/react';
import App from '../App';

// Mock the Google OAuth provider
jest.mock('@react-oauth/google', () => ({
  GoogleOAuthProvider: ({ children }) => <div>{children}</div>,
  GoogleLogin: () => <div data-testid="google-login" />,
}));

// Mock AuthContext
jest.mock('../contexts/AuthContext', () => ({
  AuthProvider: ({ children }) => <div>{children}</div>,
  useAuth: () => ({
    user: null,
    loading: false,
    isAuthenticated: false,
    login: jest.fn(),
    logout: jest.fn(),
  }),
}));

describe('App Component', () => {
  test('renders without crashing', async () => {
    render(<App />);
  });

  test('renders Home component by default', async () => {
    render(<App />);
    // Add assertions based on your Home component
    // expect(screen.getByText(/welcome/i)).toBeInTheDocument();
  });

  // Add more tests as needed
});
