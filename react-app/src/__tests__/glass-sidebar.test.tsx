import React from 'react';
import { render, screen } from '@testing-library/react';
import GlassSidebar from '../components/glass/GlassSidebar';

describe('GlassSidebar', () => {
  test('renders provided items', () => {
    const items = ['Home', 'Settings', 'Profile', 'Reports', 'Help'];
    render(<GlassSidebar items={items} />);
    for (const item of items) {
      expect(screen.getByText(item)).toBeInTheDocument();
    }
  });
});
