import React, { useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import {
  ChevronLeft,
  ChevronRight,
  FileText,
  HelpCircle,
  Home,
  Layers,
  Settings,
} from 'lucide-react';

import GlassButton from './GlassButton';

type Props = {
  items?: string[];
  id?: string;
  isOpen?: boolean;
  onClose?: () => void;
  variant?: 'app' | 'public';
  onMenuItemClick?: (item: string) => void;
};

const defaultItems = ['Home', 'Dashboard', 'Settings', 'Users', 'Help'];

export const GlassSidebar: React.FC<Props> = ({
  items = defaultItems,
  id,
  isOpen = true,
  onClose,
  variant = 'app',
  onMenuItemClick,
}) => {
  const panelRef = useRef<HTMLElement | null>(null);
  const restoreFocusRef = useRef<HTMLElement | null>(null);
  const close = useMemo(() => onClose || (() => {}), [onClose]);

  const isMobile = Boolean(window.matchMedia && window.matchMedia('(max-width: 768px)').matches);

  const [edgeOpen, setEdgeOpen] = useState(false);
  const [edgePosition, setEdgePosition] = useState<'left' | 'right'>('left');

  const publicMenuItems = [
    { icon: Home, label: 'Home', id: 'home' },
    { icon: Layers, label: 'Features', id: 'features' },
    { icon: FileText, label: 'Documentation', id: 'docs' },
    { icon: Settings, label: 'Settings', id: 'settings' },
    { icon: HelpCircle, label: 'Help & Support', id: 'help' },
  ];

  useEffect(() => {
    if (!isOpen || !isMobile) {
      return;
    }

    restoreFocusRef.current = document.activeElement as HTMLElement | null;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    // Focus the drawer panel for accessibility.
    panelRef.current!.focus();

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        close();
      }
    };

    document.addEventListener('keydown', onKeyDown);

    return () => {
      document.body.style.overflow = prevOverflow;
      document.removeEventListener('keydown', onKeyDown);
      const el = restoreFocusRef.current;
      if (el && typeof el.focus === 'function') {
        el.focus();
      }
    };
  }, [close, isMobile, isOpen]);

  if (variant === 'public') {
    const handleClick = (itemId: string) => {
      setEdgeOpen(false);
      if (onMenuItemClick) {
        onMenuItemClick(itemId);
      } else {
        void itemId;
      }
    };

    const togglePosition = () => {
      setEdgePosition((p) => (p === 'left' ? 'right' : 'left'));
    };

    return (
      <>
        <motion.button
          onClick={() => setEdgeOpen((v) => !v)}
          className="fixed z-40 backdrop-blur-2xl bg-white/25 dark:bg-black/40 border border-white/30 dark:border-white/20 shadow-[0_4px_16px_0_rgba(31,38,135,0.15)] dark:shadow-[0_4px_16px_0_rgba(0,0,0,0.3)] dark:shadow-[0_0_20px_0_rgba(139,92,246,0.1)] transition-all duration-300 ease-out hover:bg-white/35 dark:hover:bg-black/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/40 dark:focus-visible:ring-white/30"
          style={{
            [edgePosition]: edgeOpen ? 'calc(min(80vw, 20vw))' : '0',
            top: 'calc(3.5rem + 1px + 2rem)',
            borderTopLeftRadius: edgePosition === 'right' ? 'var(--radius-lg)' : '0',
            borderBottomLeftRadius: edgePosition === 'right' ? 'var(--radius-lg)' : '0',
            borderTopRightRadius: edgePosition === 'left' ? 'var(--radius-lg)' : '0',
            borderBottomRightRadius: edgePosition === 'left' ? 'var(--radius-lg)' : '0',
            padding: 'calc(1rem) calc(0.5rem)',
            width: 'calc(2.5rem)',
            height: 'calc(5rem)',
          }}
          aria-label={edgeOpen ? 'Close menu' : 'Open menu'}
          aria-expanded={edgeOpen}
          animate={{
            boxShadow: edgeOpen
              ? ['0 4px 16px 0 rgba(31,38,135,0.15)', '0 4px 16px 0 rgba(31,38,135,0.15)']
              : [
                  '0 4px 16px 0 rgba(31,38,135,0.15), 0 0 0 0 rgba(139,92,246,0.4)',
                  '0 4px 16px 0 rgba(31,38,135,0.15), 0 0 0 8px rgba(139,92,246,0)',
                ],
          }}
          transition={{
            repeat: edgeOpen ? 0 : Infinity,
            duration: 2,
            ease: 'easeOut',
          }}
        >
          {!edgeOpen ? (
            <motion.div
              className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-violet-400"
              initial={{ scale: 1, opacity: 0.8 }}
              animate={{ scale: [1, 1.2, 1], opacity: [0.8, 1, 0.8] }}
              transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
            />
          ) : null}

          <svg
            width="24"
            height="48"
            viewBox="0 0 24 48"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className="text-foreground"
            aria-hidden="true"
          >
            <motion.g
              initial={{
                opacity: edgeOpen ? 0 : 1,
                x: edgeOpen ? (edgePosition === 'left' ? -10 : 10) : 0,
              }}
              animate={{
                opacity: edgeOpen ? 0 : 1,
                x: edgeOpen ? (edgePosition === 'left' ? -10 : 10) : 0,
              }}
              transition={{ duration: 0.3, ease: 'easeOut' }}
            >
              <rect x="4" y="14" width="16" height="2" rx="1" fill="currentColor" />
              <rect x="4" y="23" width="16" height="2" rx="1" fill="currentColor" />
              <rect x="4" y="32" width="16" height="2" rx="1" fill="currentColor" />
            </motion.g>

            <motion.g
              initial={{
                opacity: edgeOpen ? 1 : 0,
                x: edgeOpen ? 0 : edgePosition === 'left' ? 10 : -10,
              }}
              animate={{
                opacity: edgeOpen ? 1 : 0,
                x: edgeOpen ? 0 : edgePosition === 'left' ? 10 : -10,
              }}
              transition={{ duration: 0.3, ease: 'easeOut' }}
            >
              {edgePosition === 'left' ? (
                <ChevronLeft className="w-6 h-6" style={{ transform: 'translateY(12px)' }} />
              ) : (
                <ChevronRight className="w-6 h-6" style={{ transform: 'translateY(12px)' }} />
              )}
            </motion.g>
          </svg>
        </motion.button>

        <AnimatePresence>
          {edgeOpen ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3, ease: 'easeOut' }}
              onClick={() => setEdgeOpen(false)}
              className="fixed inset-0 z-30 backdrop-blur-sm bg-black/20 dark:bg-black/40"
            />
          ) : null}
        </AnimatePresence>

        <AnimatePresence>
          {edgeOpen ? (
            <motion.aside
              initial={{ [edgePosition]: '-100%' }}
              animate={{ [edgePosition]: 0 }}
              exit={{ [edgePosition]: '-100%' }}
              transition={{ duration: 0.3, ease: 'easeOut' }}
              className="fixed z-30 backdrop-blur-2xl bg-white/25 dark:bg-black/40 shadow-[8px_0_32px_0_rgba(31,38,135,0.15)] dark:shadow-[8px_0_32px_0_rgba(0,0,0,0.3)] dark:shadow-[0_0_40px_0_rgba(139,92,246,0.1)]"
              style={{
                [edgePosition]: 0,
                top: 0,
                height: '100vh',
                width: 'calc(min(80vw, 20vw))',
                borderLeft: edgePosition === 'right' ? '1px solid rgba(255, 255, 255, 0.2)' : 'none',
                borderRight: edgePosition === 'left' ? '1px solid rgba(255, 255, 255, 0.2)' : 'none',
              }}
            >
              <div className="flex flex-col h-full" style={{ padding: 'calc(2rem) calc(1rem)' }}>
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-lg font-medium">Menu</h3>
                  <button
                    onClick={togglePosition}
                    className="p-2 rounded-[var(--radius-lg)] hover:bg-white/30 dark:hover:bg-black/50 transition-all duration-300 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/40 dark:focus-visible:ring-white/30"
                    aria-label={`Switch to ${edgePosition === 'left' ? 'right' : 'left'} side`}
                    title={`Move to ${edgePosition === 'left' ? 'right' : 'left'} side`}
                  >
                    <svg
                      width="20"
                      height="20"
                      viewBox="0 0 20 20"
                      fill="none"
                      xmlns="http://www.w3.org/2000/svg"
                      className="text-foreground"
                      aria-hidden="true"
                    >
                      {edgePosition === 'left' ? (
                        <>
                          <rect x="2" y="2" width="7" height="16" rx="2" fill="currentColor" opacity="0.3" />
                          <rect x="11" y="2" width="7" height="16" rx="2" stroke="currentColor" strokeWidth="1.5" />
                          <path
                            d="M14 10L16 10M16 10L15 9M16 10L15 11"
                            stroke="currentColor"
                            strokeWidth="1.5"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </>
                      ) : (
                        <>
                          <rect x="11" y="2" width="7" height="16" rx="2" fill="currentColor" opacity="0.3" />
                          <rect x="2" y="2" width="7" height="16" rx="2" stroke="currentColor" strokeWidth="1.5" />
                          <path
                            d="M6 10L4 10M4 10L5 9M4 10L5 11"
                            stroke="currentColor"
                            strokeWidth="1.5"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </>
                      )}
                    </svg>
                  </button>
                </div>

                <nav className="flex flex-col gap-2 flex-1" aria-label="Public menu">
                  {publicMenuItems.map((item, index) => {
                    const Icon = item.icon;
                    return (
                      <motion.button
                        key={item.id}
                        initial={{ opacity: 0, x: edgePosition === 'left' ? -20 : 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.05, duration: 0.3, ease: 'easeOut' }}
                        onClick={() => handleClick(item.id)}
                        className="w-full flex items-center gap-3 px-4 py-3 rounded-[var(--radius-lg)] backdrop-blur-xl bg-white/20 dark:bg-black/30 border border-white/30 dark:border-white/20 hover:bg-white/30 dark:hover:bg-black/40 transition-all duration-300 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/40 dark:focus-visible:ring-white/30 hover:-translate-y-0.5"
                      >
                        <Icon className="w-5 h-5 flex-shrink-0" aria-hidden="true" />
                        <span className="text-left truncate">{item.label}</span>
                      </motion.button>
                    );
                  })}
                </nav>

                <div
                  className="sm:hidden flex flex-col gap-2"
                  style={{
                    marginTop: 'auto',
                    paddingTop: 'calc(1.5rem)',
                    borderTop: '1px solid rgba(255, 255, 255, 0.2)',
                  }}
                >
                  <GlassButton variant="ghost" className="w-full">
                    Login
                  </GlassButton>
                  <GlassButton variant="primary" className="w-full">
                    Sign Up
                  </GlassButton>
                </div>
              </div>
            </motion.aside>
          ) : null}
        </AnimatePresence>

        <style>{`
          @media (max-width: 640px) {
            aside[style*="width"] {
              width: 80vw !important;
            }
          }
        `}</style>
      </>
    );
  }

  return (
    <>
      {isMobile ? (
        isOpen ? (
          <div
            className="glass-drawer-overlay"
            data-testid="drawer-overlay"
            role="presentation"
            onClick={close}
          >
            <aside
              className="glass glass-drawer-panel"
              data-state="open"
              role="navigation"
              aria-label="Side menu"
              tabIndex={-1}
              ref={(el) => {
                panelRef.current = el;
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <ul className="glass-sidebar-list">
                {items.map((i) => (
                  <li key={i} className="glass-sidebar-item">
                    {i}
                  </li>
                ))}
              </ul>
            </aside>
          </div>
        ) : null
      ) : (
        <aside
          id={id}
          className="glass glass-sidebar"
          style={{ width: 'var(--sidebar-w)', maxWidth: '400px' }}
          aria-label="Sidebar"
          hidden={!isOpen}
        >
          <ul className="glass-sidebar-list">
            {items.map((i) => (
              <li key={i} className="glass-sidebar-item">
                {i}
              </li>
            ))}
          </ul>
        </aside>
      )}
    </>
  );
};

export default GlassSidebar;
