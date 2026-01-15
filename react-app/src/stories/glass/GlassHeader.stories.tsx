import React, { useState } from 'react';
import type { Meta, StoryObj } from '@storybook/react';
import { expect, userEvent, within } from '@storybook/test';

import GlassHeader from '../../components/glass/GlassHeader';

const meta: Meta<typeof GlassHeader> = {
  title: 'Glass/Header',
  component: GlassHeader,
};
export default meta;

type Story = StoryObj<typeof GlassHeader>;

export const Public: Story = {
  args: {
    title: 'Home',
    variant: 'public',
  },
};

function AppHeaderStory() {
  const [open, setOpen] = useState(false);
  return (
    <GlassHeader
      title="Dashboard"
      variant="app"
      menuControlsId="app-shell-sidebar"
      isMenuOpen={open}
      onToggleMenu={() => setOpen((v) => !v)}
    />
  );
}

export const App: Story = {
  render: () => <AppHeaderStory />,
};

export const AppInteraction: Story = {
  render: () => <AppHeaderStory />,
  play: async ({ canvasElement }) => {
    const c = within(canvasElement);
    const btn = await c.findByRole('button', { name: /menu/i });
    expect(btn).toHaveAttribute('aria-expanded', 'false');
    await userEvent.click(btn);
    expect(btn).toHaveAttribute('aria-expanded', 'true');
  },
};
