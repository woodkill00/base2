import '@testing-library/jest-dom';
import React from 'react';
import { act, render, screen, waitForElementToBeRemoved } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import GlassSidebar from '../components/glass/GlassSidebar';

describe('GlassSidebar (public variant)', () => {
  test('opens, toggles side, and calls onMenuItemClick', async () => {
    const user = userEvent.setup();
    const onMenuItemClick = jest.fn();

    const { container } = render(
      <GlassSidebar variant="public" onMenuItemClick={onMenuItemClick} />
    );

    // Default: closed edge button.
    expect(screen.getByLabelText(/open menu/i)).toBeInTheDocument();

    // Open.
    await act(async () => {
      await user.click(screen.getByLabelText(/open menu/i));
    });
    expect(await screen.findByText('Menu')).toBeInTheDocument();
    expect(await screen.findByRole('navigation', { name: /public menu/i })).toBeInTheDocument();

    // Toggle side (left -> right -> left -> right) to cover both branches,
    // and also ensure we hit the "closed button" render path with edgePosition="right".
    await act(async () => {
      await user.click(screen.getByLabelText(/switch to right side/i));
    });
    expect(await screen.findByLabelText(/switch to left side/i)).toBeInTheDocument();

    await act(async () => {
      await user.click(screen.getByLabelText(/switch to left side/i));
    });
    expect(await screen.findByLabelText(/switch to right side/i)).toBeInTheDocument();

    await act(async () => {
      await user.click(screen.getByLabelText(/switch to right side/i));
    });
    expect(await screen.findByLabelText(/switch to left side/i)).toBeInTheDocument();

    // Click a menu item and ensure callback + close.
    await act(async () => {
      await user.click(screen.getByRole('button', { name: /features/i }));
    });
    expect(onMenuItemClick).toHaveBeenCalledWith('features');
    await waitForElementToBeRemoved(() => screen.getByText('Menu'));
    expect(screen.getByLabelText(/open menu/i)).toBeInTheDocument();

    // Re-open and close via backdrop click.
    await act(async () => {
      await user.click(screen.getByLabelText(/open menu/i));
    });
    expect(await screen.findByText('Menu')).toBeInTheDocument();

    const backdrop = container.querySelector('.fixed.inset-0');
    expect(backdrop).toBeTruthy();
    await act(async () => {
      await user.click(backdrop as Element);
    });
    await waitForElementToBeRemoved(() => screen.getByText('Menu'));
  });

  test('closes even when onMenuItemClick is not provided', async () => {
    const user = userEvent.setup();

    render(<GlassSidebar variant="public" />);

    await act(async () => {
      await user.click(screen.getByLabelText(/open menu/i));
    });
    expect(await screen.findByText('Menu')).toBeInTheDocument();

    await act(async () => {
      await user.click(screen.getByRole('button', { name: /documentation/i }));
    });
    await waitForElementToBeRemoved(() => screen.getByText('Menu'));
  });
});
