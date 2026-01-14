import type { Meta, StoryObj } from '@storybook/react';
import React, { useState } from 'react';
import GlassModal from '../../components/glass/GlassModal';
import GlassButton from '../../components/glass/GlassButton';

const meta: Meta = {
  title: 'Glass/Modal Design Parity',
};
export default meta;

export const OpenClose: StoryObj = {
  render: () => {
    const ModalDemo: React.FC = () => {
      const [open, setOpen] = useState(false);
      return (
        <div style={{ padding: 16 }}>
          <GlassButton onClick={() => setOpen(true)}>Open Modal</GlassButton>
          <GlassModal open={open} onClose={() => setOpen(false)}>
            <div style={{ display: 'grid', gap: 8 }}>
              <h3>Sub-page Modal</h3>
              <p>Demonstrates parity with design: ESC closes; focusable content present.</p>
              <GlassButton onClick={() => setOpen(false)}>Close</GlassButton>
            </div>
          </GlassModal>
        </div>
      );
    };
    return <ModalDemo />;
  },
};
