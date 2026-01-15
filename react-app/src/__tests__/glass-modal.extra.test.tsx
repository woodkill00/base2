import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
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
    const onClose = jest.fn();
    render(
      <GlassModal open onClose={onClose}>
        <button>Inside</button>
      </GlassModal>
    );
    fireEvent.keyDown(document, { key: 'Enter' });
    expect(onClose).not.toHaveBeenCalled();
  });

  test('overlay click closes', async () => {
    const user = userEvent.setup();
    const onClose = jest.fn();
    render(
      <GlassModal open onClose={onClose}>
        <button>Inside</button>
      </GlassModal>
    );
    await user.click(screen.getByTestId('modal-overlay'));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  test('click inside dialog does not close', async () => {
    const user = userEvent.setup();
    const onClose = jest.fn();
    render(
      <GlassModal open onClose={onClose}>
        <button>Inside</button>
      </GlassModal>
    );

    await user.click(screen.getByRole('dialog'));
    expect(onClose).not.toHaveBeenCalled();
  });

  test('cleanup handles activeElement=null safely', () => {
    const onClose = jest.fn();
    const originalActiveElementDescriptor = Object.getOwnPropertyDescriptor(
      Document.prototype,
      'activeElement'
    );

    Object.defineProperty(Document.prototype, 'activeElement', {
      configurable: true,
      get: () => null,
    });

    const { unmount } = render(
      <GlassModal open onClose={onClose}>
        <button>Inside</button>
      </GlassModal>
    );

    expect(document.activeElement).toBeNull();
    unmount();

    if (originalActiveElementDescriptor) {
      Object.defineProperty(Document.prototype, 'activeElement', originalActiveElementDescriptor);
    }
  });
});
