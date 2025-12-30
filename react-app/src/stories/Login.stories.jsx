import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import Login from '../pages/Login.jsx';
import { AuthProvider } from '../contexts/AuthContext';

export default {
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

export const Default = {};
