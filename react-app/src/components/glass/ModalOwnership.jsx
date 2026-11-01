import { useEffect, useRef } from 'react';
import { useScrollTargetLock } from '../../lib/scrollTarget';

const owners = new WeakMap();
export function acquireModalBackground(root) {
  let entry = owners.get(root);
  if (!entry) {
    entry = { count: 0, inert: root.hasAttribute('inert'), isolation: root.style.isolation };
    owners.set(root, entry);
    root.setAttribute('inert', '');
    root.style.isolation = 'isolate';
  }
  entry.count++;
  let released = false;
  return () => {
    if (released) return;
    released = true;
    if (--entry.count) return;
    if (!entry.inert) root.removeAttribute('inert');
    root.style.isolation = entry.isolation;
    owners.delete(root);
  };
}

// Render within the shell's React scroll-target context, with the dialog portaled
// outside its DOM root. Background stacking and interaction ownership end together.
// This is the single active Operations dialog contract, not a nested modal stack:
// lock reference counts do not arbitrate competing focus or keydown handlers.
export default function ModalOwnership({ dialogRef, initialFocusRef, returnFocusRef, onClose }) {
  useScrollTargetLock(true, true);
  const close = useRef(onClose);
  close.current = onClose;
  useEffect(() => {
    const dialog = dialogRef.current;
    const returnFocus = returnFocusRef.current;
    const releases = [...document.querySelectorAll('.app-shell-root')]
      .filter((root) => !root.contains(dialog))
      .map(acquireModalBackground);
    const controls = () =>
      [
        ...dialog.querySelectorAll(
          'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex="0"]'
        ),
      ].filter((node) => !node.closest('[inert]'));
    const onKey = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        event.stopPropagation();
        close.current();
      } else if (event.key === 'Tab') {
        const nodes = controls(),
          first = nodes[0],
          last = nodes[nodes.length - 1];
        if (!first) {
          event.preventDefault();
          initialFocusRef.current?.focus({ preventScroll: true });
        } else if (!nodes.includes(document.activeElement)) {
          event.preventDefault();
          (event.shiftKey ? last : first).focus();
        } else if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    const onFocus = (event) => {
      if (!dialog.contains(event.target)) initialFocusRef.current?.focus({ preventScroll: true });
    };
    document.addEventListener('keydown', onKey, true);
    document.addEventListener('focusin', onFocus);
    initialFocusRef.current?.focus({ preventScroll: true });
    return () => {
      document.removeEventListener('keydown', onKey, true);
      document.removeEventListener('focusin', onFocus);
      releases.reverse().forEach((release) => release());
      if (returnFocus?.isConnected) returnFocus.focus({ preventScroll: true });
    };
  }, [dialogRef, initialFocusRef, returnFocusRef]);
  return null;
}
