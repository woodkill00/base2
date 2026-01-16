import { MemoryRouter } from 'react-router-dom';

import Home from '../../pages/Home';

const meta = {
  title: 'Pages/Home',
  component: Home,
  parameters: {
    layout: 'fullscreen',
  },
};

export default meta;

export const Default = () => (
  <MemoryRouter>
    <Home />
  </MemoryRouter>
);
