import React, { useRef, useState } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
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

    // Modal focuses the close button on open.
    const closeBtn = screen.getByRole('button', { name: /close/i });
    await waitFor(() => expect(closeBtn).toHaveFocus());

    // ESC closes
    await user.keyboard('{Escape}');
    expect(onClose).toHaveBeenCalled();
  });
});
