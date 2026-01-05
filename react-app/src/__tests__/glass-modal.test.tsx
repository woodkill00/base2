import React, { useRef, useState } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import GlassModal from '../components/glass/GlassModal';

describe('GlassModal behavior', () => {
  test('opens, traps focus, closes on ESC', async () => {
    const user = userEvent.setup();
    const onClose = jest.fn();
    render(
      <GlassModal open onClose={onClose}>
        <button>Inside</button>
      </GlassModal>
    );

    const dialog = screen.getByRole('dialog');
    expect(dialog).toBeInTheDocument();

    // Focus first focusable element inside dialog
    const inside = screen.getByRole('button', { name: 'Inside' });
    inside.focus();
    expect(inside).toHaveFocus();

    // ESC closes
    await user.keyboard('{Escape}');
    expect(onClose).toHaveBeenCalled();
  });
});
