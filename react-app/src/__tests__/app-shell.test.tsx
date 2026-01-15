import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AppShell from '../components/glass/AppShell';

describe('AppShell', () => {
  test('renders header and content; side menu opens via toggle', async () => {
    const user = userEvent.setup();
    render(
      <AppShell headerTitle="Title" sidebarItems={["One","Two","Three","Four","Five"]}>
        <div>Content</div>
      </AppShell>
    );
    expect(screen.getByText('Title')).toBeInTheDocument();
    expect(screen.getByText('Content')).toBeInTheDocument();

    const sidebar = screen.getByLabelText('Sidebar');
    expect(sidebar).not.toBeVisible();
    await user.click(screen.getByRole('button', { name: /menu/i }));
    expect(sidebar).toBeVisible();
    expect(screen.getByText('One')).toBeInTheDocument();
  });
});
