import React, { useState } from 'react';
import { Meta, StoryObj } from '@storybook/react';
import { userEvent, within, expect } from '@storybook/test';
import GlassModal from '../../components/glass/GlassModal';
import GlassButton from '../../components/glass/GlassButton';

const meta: Meta<typeof GlassModal> = {
  title: 'Glass/Modal',
  component: GlassModal,
};
export default meta;

type Story = StoryObj<typeof GlassModal>;

function ModalStory() {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <GlassButton variant="primary" onClick={() => setOpen(true)}>Open</GlassButton>
      <GlassModal open={open} onClose={() => setOpen(false)}>
        <h3>Modal Title</h3>
        <p>Content</p>
        <GlassButton variant="secondary" onClick={() => setOpen(false)}>Close</GlassButton>
      </GlassModal>
    </div>
  );
}

export const Basic: Story = { render: () => <ModalStory /> };

export const Interaction: Story = {
  render: () => <ModalStory />,
  play: async ({ canvasElement }) => {
    const c = within(canvasElement);
    const openBtn = await c.getByRole('button', { name: /open/i });
    await userEvent.click(openBtn);
    const dialog = await c.findByRole('dialog');
    expect(dialog).toBeInTheDocument();
    const closeBtn = await c.findByRole('button', { name: /close/i });
    await userEvent.click(closeBtn);
    await expect(c.queryByRole('dialog')).not.toBeInTheDocument();
  },
};
