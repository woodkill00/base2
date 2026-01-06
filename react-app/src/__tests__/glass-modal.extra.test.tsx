import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import GlassModal from '../components/glass/GlassModal';

describe('GlassModal extra coverage', () => {
  test('does not render when open=false', () => {
    const onClose = jest.fn();
    render(
      <GlassModal open={false} onClose={onClose}>
        <button>Inside</button>
      </GlassModal>
    );
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  test('non-escape keys do not trigger onClose', async () => {
    const user = userEvent.setup();
    const onClose = jest.fn();
    render(
      <GlassModal open onClose={onClose}>
        <button>Inside</button>
      </GlassModal>
    );
    const inside = screen.getByRole('button', { name: 'Inside' });
    inside.focus();
    await user.keyboard('{Enter}');
    expect(onClose).not.toHaveBeenCalled();
  });
});
