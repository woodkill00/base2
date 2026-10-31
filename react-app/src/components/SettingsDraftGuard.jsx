import { useCallback, useContext, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import './settings-draft-guard.css';
import { UNSAFE_DataRouterContext, useBlocker } from 'react-router-dom';

const copy = {
  en: {
    title: 'Leave settings?',
    body: 'Leaving discards local drafts, not requests already sent. Stay to keep editing.',
    stay: 'Stay',
    discard: 'Discard and leave',
  },
  de: {
    title: 'Einstellungen verlassen?',
    body: 'Beim Verlassen werden lokale Entwürfe verworfen, nicht bereits gesendete Anfragen. Bleiben Sie, um weiterzubearbeiten.',
    stay: 'Bleiben',
    discard: 'Verwerfen und verlassen',
  },
  ar: {
    title: 'مغادرة الإعدادات؟',
    body: 'ستُتجاهل المسودات المحلية عند المغادرة، وليس الطلبات المرسلة بالفعل. ابق لمتابعة التحرير.',
    stay: 'البقاء',
    discard: 'تجاهل ومغادرة',
  },
};

function RouterDraftGuard({ dirty, locale }) {
  const focus = useRef(null);
  const overlay = useRef(null);
  const restoreFocus = useRef(false);
  const stayButton = useRef(null);
  const discardButton = useRef(null);
  const decided = useRef(false);
  const pending = useRef(false);
  const shouldBlock = useCallback(
    ({ nextLocation }) => {
      // Categories share the same mounted drafts. Authentication recovery must never
      // be held hostage by an obsolete form after revocation/session expiry.
      const internal = /^\/settings(?:\/|$)/.test(nextLocation.pathname);
      const authentication = /^\/(?:login|logout|auth)(?:\/|$)/.test(nextLocation.pathname);
      if (!dirty || internal || authentication) return false;
      if (!pending.current) focus.current = document.activeElement;
      pending.current = true;
      return true;
    },
    [dirty]
  );
  const blocker = useBlocker(shouldBlock);
  const open = blocker.state === 'blocked';
  const text = copy[locale] || copy.en;
  useEffect(() => {
    if (!open) {
      pending.current = false;
      return undefined;
    }
    decided.current = false;
    const overflow = document.body.style.overflow;
    // The body portal must remain outside every inert background ancestor. Include
    // the shell explicitly, plus siblings such as application toasts/other roots.
    const background = [
      ...new Set([
        ...document.querySelectorAll('.app-shell-root'),
        ...[...document.body.children].filter(
          (node) => node !== overlay.current && !['SCRIPT', 'STYLE', 'LINK'].includes(node.tagName)
        ),
      ]),
    ];
    const priorInert = background.map((node) => node.getAttribute('inert'));
    background.forEach((node) => node.setAttribute('inert', ''));
    document.body.style.overflow = 'hidden';
    const containFocus = (event) => {
      if (!overlay.current?.contains(event.target)) stayButton.current?.focus();
    };
    document.addEventListener('focusin', containFocus, true);
    stayButton.current?.focus();
    return () => {
      document.removeEventListener('focusin', containFocus, true);
      background.forEach((node, index) => {
        if (priorInert[index] === null) node.removeAttribute('inert');
        else node.setAttribute('inert', priorInert[index]);
      });
      document.body.style.overflow = overflow;
      if (restoreFocus.current) {
        restoreFocus.current = false;
        const available = (node) => {
          if (
            !node?.isConnected ||
            node === document.body ||
            node.disabled ||
            node.closest('[inert], [hidden], [aria-hidden="true"]')
          )
            return false;
          for (let ancestor = node; ancestor; ancestor = ancestor.parentElement) {
            const style = getComputedStyle(ancestor);
            if (style.display === 'none' || style.visibility === 'hidden') return false;
          }
          return true;
        };
        const target = [
          focus.current,
          document.getElementById('settings-detail'),
          document.getElementById('main-content'),
        ].find(available);
        target?.focus({ preventScroll: true });
      }
    };
  }, [open]);
  const stay = () => {
    if (decided.current) return;
    decided.current = true;
    pending.current = false;
    restoreFocus.current = true;
    blocker.reset();
  };
  if (!open) return null;
  return createPortal(
    <div
      ref={overlay}
      className="glass-modal-overlay settings-draft-overlay text-slate-900 dark:text-slate-100"
      role="presentation"
      onPointerDown={(event) => {
        // A backdrop click must not blur the active modal control onto body,
        // where shell keyboard shortcuts could otherwise receive the next key.
        if (event.target === event.currentTarget) event.preventDefault();
      }}
      lang={locale}
      dir={locale === 'ar' ? 'rtl' : 'ltr'}
    >
      <div
        className="glass glass-modal"
        role="alertdialog"
        tabIndex={-1}
        aria-modal="true"
        aria-labelledby="settings-leave-title"
        aria-describedby="settings-leave-description"
        onKeyDown={(event) => {
          // Do not let a shell drawer or command palette consume modal keystrokes.
          event.stopPropagation();
          if (event.key === 'Escape') {
            event.preventDefault();
            stay();
          }
          if (event.key === 'Tab') {
            event.preventDefault();
            (document.activeElement === stayButton.current
              ? discardButton
              : stayButton
            ).current?.focus();
          }
        }}
      >
        <h2 id="settings-leave-title" className="font-semibold">
          {text.title}
        </h2>
        <p id="settings-leave-description" className="my-4">
          {text.body}
        </p>
        <div className="flex flex-wrap gap-3">
          <button
            ref={stayButton}
            type="button"
            className="glass glass-btn glass-interactive"
            onClick={stay}
          >
            {text.stay}
          </button>
          <button
            ref={discardButton}
            type="button"
            className="glass glass-btn glass-interactive"
            onClick={() => {
              if (decided.current) return;
              decided.current = true;
              pending.current = false;
              blocker.proceed();
            }}
          >
            {text.discard}
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}

export default function SettingsDraftGuard(props) {
  // Isolated declarative-router consumers have only the beforeunload guard;
  // the application always supplies a data router and exercises the full guard.
  const router = useContext(UNSAFE_DataRouterContext);
  return router ? <RouterDraftGuard {...props} /> : null;
}
