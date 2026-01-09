import React from 'react';
import { render, screen } from '@testing-library/react';
import AppShell from '../components/glass/AppShell';

describe('AppShell', () => {
  test('renders header, sidebar, content, footer', () => {
    render(
      <AppShell headerTitle="Title" sidebarItems={["One","Two","Three","Four","Five"]}>
        <div>Content</div>
      </AppShell>
    );
    expect(screen.getByText('Title')).toBeInTheDocument();
    expect(screen.getByText('One')).toBeInTheDocument();
    expect(screen.getByText('Content')).toBeInTheDocument();
  });
});
