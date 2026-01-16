import React from 'react';
import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import TestMemoryRouter from '../test/TestMemoryRouter';
import AppShell from '../components/glass/AppShell';

describe('AppShell', () => {
  test('renders header and content; side menu opens via toggle', async () => {
    const user = userEvent.setup();
    render(
      <TestMemoryRouter>
        <AppShell headerTitle="Title" sidebarItems={["One", "Two", "Three", "Four", "Five"]}>
          <div>Content</div>
        </AppShell>
      </TestMemoryRouter>
    );
    expect(screen.getByText('Title')).toBeInTheDocument();
    expect(screen.getByText('Content')).toBeInTheDocument();

    const sidebar = screen.getByLabelText('Sidebar');
    expect(sidebar).not.toBeVisible();
    await act(async () => {
      await user.click(screen.getByRole('button', { name: /menu/i }));
    });
    expect(await screen.findByText('One')).toBeInTheDocument();
    expect(sidebar).toBeVisible();
  });
});
