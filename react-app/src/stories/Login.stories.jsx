import { MemoryRouter } from 'react-router-dom';
import Login from '../pages/Login.jsx';
import { AuthProvider } from '../contexts/AuthContext';

const meta = {
  title: 'Pages/Login',
  component: Login,
  decorators: [
    (Story) => (
      <AuthProvider>
        <MemoryRouter>
          <Story />
        </MemoryRouter>
      </AuthProvider>
    ),
  ],
};
export default meta;

export const Default = {};
