import React from 'react';
import { MemoryRouter } from 'react-router-dom';

import Home from '../../pages/Home';

export default {
  title: 'Pages/Home',
  component: Home,
  parameters: {
    layout: 'fullscreen',
  },
};

export const Default = () => (
  <MemoryRouter>
    <Home />
  </MemoryRouter>
);
