import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity,
  ArrowDown,
  ArrowUp,
  Bell,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  Command,
  Heart,
  History,
  LayoutGrid,
  LockKeyhole,
  LogOut,
  Search,
  Server,
  Settings,
  Share2,
  Shield,
  ShieldCheck,
  User,
  Zap,
} from 'lucide-react';

const sectionItems = [
  { id: 'home', label: 'Home', target: 'home-page', icon: LayoutGrid },
  { id: 'features', label: 'Features', target: 'features', icon: Zap },
  { id: 'command', label: 'Command', target: 'base2-obsidian-ops', icon: Search },
  { id: 'security', label: 'Security', target: 'base2-thermal-security', icon: ShieldCheck },
  { id: 'contact', label: 'Contact', target: 'contact', icon: Server },
];

const utilityItems = [
  { label: 'Settings', icon: Settings, safe: false },
  { label: 'Notifications', icon: Bell, safe: true },
  { label: 'Share', icon: Share2, safe: true },
  { label: 'History', icon: History, safe: true },
  { label: 'Security', icon: Shield, safe: true },
  { label: 'Automation', icon: Zap, safe: false },
  { label: 'Search', icon: Search, safe: true },
  { label: 'Profile', icon: User, safe: true },
  { label: 'Favorites', icon: Heart, safe: true },
  { label: 'Sign out', icon: LogOut, safe: false },
];

const commandActions = [
  { id: 'go-home', label: 'Go to home', sectionId: 'home', safe: true },
  { id: 'go-features', label: 'Review Base2 features', sectionId: 'features', safe: true },
  { id: 'go-command', label: 'Open command operations', sectionId: 'command', safe: true },
  { id: 'go-security', label: 'Inspect security surface', sectionId: 'security', safe: true },
  { id: 'go-contact', label: 'Contact Base2', sectionId: 'contact', safe: true },
  { id: 'admin-debug', label: 'Admin diagnostics', safe: false },
];

const colorSchemes = [
  {
    id: 'volcanic',
    label: 'Volcanic',
    primary: '#ff3131',
    accent: '#ff6321',
    surface: '#131313',
  },
  {
    id: 'ember',
    label: 'Ember',
    primary: '#ff7a18',
    accent: '#ffd166',
    surface: '#17120f',
  },
  {
    id: 'basalt',
    label: 'Basalt',
    primary: '#66e3ff',
    accent: '#b5f7ff',
    surface: '#101518',
  },
];

const UTILITY_SELECTOR_FALLBACK = {
  top: '183px',
  left: '50%',
  width: '42px',
  height: '42px',
};

const findSection = (item) => {
  if (typeof document === 'undefined') return null;
  return document.querySelector(`[data-testid="${item.target}"]`) || document.getElementById(item.target);
};

const getSectionElements = () =>
  sectionItems
    .map((item) => ({ item, element: findSection(item) }))
    .filter(({ element }) => Boolean(element));

const getScrollMetrics = () => {
  if (typeof window === 'undefined' || typeof document === 'undefined') {
    return { progress: 0, canAscend: false, canDescend: true };
  }

  const root = document.documentElement;
  const scrollTop = window.scrollY || root.scrollTop || 0;
  const maxScroll = Math.max(1, root.scrollHeight - window.innerHeight);
  const progress = Math.min(100, Math.max(0, (scrollTop / maxScroll) * 100));

  return {
    progress,
    canAscend: scrollTop > 12,
    canDescend: scrollTop < maxScroll - 12,
  };
};

const readActiveSection = () => {
  if (typeof window === 'undefined') return sectionItems[0].id;
  const sections = getSectionElements();
  let active = sections[0]?.item.id || sectionItems[0].id;

  sections.forEach(({ item, element }) => {
    const rect = element.getBoundingClientRect();
    if (rect.top <= Math.min(220, window.innerHeight * 0.34)) {
      active = item.id;
    }
  });

  return active;
};

const HomeObsidianNavigation = ({ onNavigate }) => {
  const [isLeftOpen, setIsLeftOpen] = useState(false);
  const [isRightOpen, setIsRightOpen] = useState(false);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [navButtonsEnabled, setNavButtonsEnabled] = useState(true);
  const [activeSection, setActiveSection] = useState('home');
  const [activeUtilitySlot, setActiveUtilitySlot] = useState(utilityItems.length + 4);
  const [utilitySelectorStyle, setUtilitySelectorStyle] = useState(UTILITY_SELECTOR_FALLBACK);
  const [colorSchemeId, setColorSchemeId] = useState('volcanic');
  const [scrollState, setScrollState] = useState(getScrollMetrics);
  const movementClickTimer = useRef(null);
  const lastMovementClick = useRef({ direction: 0, time: 0 });
  const leftMenuRef = useRef(null);
  const utilityScrollRef = useRef(null);
  const utilityItemRefs = useRef([]);
  const utilityScrollFrame = useRef(null);
  const utilitySnapTimer = useRef(null);
  const activeUtilitySlotRef = useRef(activeUtilitySlot);
  const movementTargetIndexRef = useRef(0);
  const movementScrollLockUntilRef = useRef(0);

  const visibleUtilityItems = useMemo(
    () => [...utilityItems, ...utilityItems, ...utilityItems],
    []
  );
  const utilityLoopOffset = utilityItems.length;
  const normalizeUtilitySlot = useCallback((index) => {
    const length = utilityItems.length;
    return utilityLoopOffset + ((index % length) + length) % length;
  }, [utilityLoopOffset]);
  const activeColorScheme = colorSchemes.find((scheme) => scheme.id === colorSchemeId) || colorSchemes[0];

  const updateScrollState = useCallback(() => {
    setScrollState(getScrollMetrics());
    const nextActiveSection = readActiveSection();
    setActiveSection(nextActiveSection);
    if (Date.now() > movementScrollLockUntilRef.current) {
      const nextIndex = sectionItems.findIndex((item) => item.id === nextActiveSection);
      if (nextIndex >= 0) {
        movementTargetIndexRef.current = nextIndex;
      }
    }
  }, []);

  useEffect(() => {
    activeUtilitySlotRef.current = activeUtilitySlot;
  }, [activeUtilitySlot]);

  useEffect(() => {
    const index = sectionItems.findIndex((item) => item.id === activeSection);
    if (index >= 0 && Date.now() > movementScrollLockUntilRef.current) {
      movementTargetIndexRef.current = index;
    }
  }, [activeSection]);

  const centerUtilitySlot = useCallback((index, behavior = 'auto') => {
    const normalizedIndex = normalizeUtilitySlot(index);
    const scrollEl = utilityScrollRef.current;
    const selectedEl = utilityItemRefs.current[normalizedIndex];
    if (!scrollEl || !selectedEl) return;
    if (normalizedIndex !== activeUtilitySlotRef.current) {
      activeUtilitySlotRef.current = normalizedIndex;
      setActiveUtilitySlot(normalizedIndex);
    }

    const itemCenter = selectedEl.offsetTop + selectedEl.offsetHeight / 2;
    scrollEl.scrollTo({
      top: Math.max(0, itemCenter - scrollEl.clientHeight / 2),
      behavior,
    });
  }, [normalizeUtilitySlot]);

  const updateUtilitySelectionFromScroll = useCallback((shouldSettle = false) => {
    const scrollEl = utilityScrollRef.current;
    if (!scrollEl || typeof window === 'undefined') return;

    if (utilityScrollFrame.current) {
      window.cancelAnimationFrame(utilityScrollFrame.current);
    }

    utilityScrollFrame.current = window.requestAnimationFrame(() => {
      utilityScrollFrame.current = null;
      const viewportCenter = scrollEl.scrollTop + scrollEl.clientHeight / 2;
      let nextSlot = normalizeUtilitySlot(activeUtilitySlotRef.current);
      let nearestDistance = Number.POSITIVE_INFINITY;

      utilityItemRefs.current.forEach((itemEl, index) => {
        if (!itemEl) return;
        if (itemEl.getAttribute('aria-disabled') === 'true' || itemEl.classList.contains('is-locked')) return;
        const itemCenter = itemEl.offsetTop + itemEl.offsetHeight / 2;
        const distance = Math.abs(itemCenter - viewportCenter);
        if (distance < nearestDistance) {
          nearestDistance = distance;
          nextSlot = index;
        }
      });

      const normalizedSlot = normalizeUtilitySlot(nextSlot);
      if (normalizedSlot !== nextSlot && utilityItemRefs.current[nextSlot]) {
        const currentLoopEl = utilityItemRefs.current[nextSlot];
        const middleLoopEl = utilityItemRefs.current[normalizedSlot];
        if (currentLoopEl && middleLoopEl) {
          scrollEl.scrollTop += middleLoopEl.offsetTop - currentLoopEl.offsetTop;
        }
      }
      const selectedEl = utilityItemRefs.current[normalizedSlot];
      if (!selectedEl) return;
      const iconEl = selectedEl.querySelector('svg');
      const scrollRect = scrollEl.getBoundingClientRect();
      const iconRect = iconEl ? iconEl.getBoundingClientRect() : null;
      const iconTop = iconRect
        ? iconRect.top - scrollRect.top + scrollEl.scrollTop
        : selectedEl.offsetTop + Math.max(0, (selectedEl.offsetHeight - 26) / 2);
      const iconLeft = iconRect
        ? iconRect.left - scrollRect.left
        : selectedEl.offsetLeft + Math.max(0, (selectedEl.offsetWidth - 26) / 2);
      const iconHeight = iconRect ? iconRect.height : 26;
      const iconWidth = iconRect ? iconRect.width : 26;
      activeUtilitySlotRef.current = normalizedSlot;
      setActiveUtilitySlot(normalizedSlot);
      setUtilitySelectorStyle({
        top: `${iconTop + iconHeight / 2 - 32}px`,
        left: `${iconLeft + iconWidth / 2}px`,
        width: '64px',
        height: '64px',
      });

      if (shouldSettle) {
        if (utilitySnapTimer.current) {
          window.clearTimeout(utilitySnapTimer.current);
        }
        utilitySnapTimer.current = window.setTimeout(() => {
          utilitySnapTimer.current = null;
          centerUtilitySlot(normalizedSlot, 'smooth');
        }, 120);
      }
    });
  }, [centerUtilitySlot, normalizeUtilitySlot]);

  const handleUtilityWheel = useCallback((event) => {
    event.preventDefault();
    const direction = event.deltaY >= 0 ? 1 : -1;
    const length = utilityItems.length;
    const activeBaseIndex = ((activeUtilitySlotRef.current - utilityLoopOffset) % length + length) % length;
    let nextIndex = normalizeUtilitySlot(activeBaseIndex + direction);

    for (let step = 1; step <= length; step += 1) {
      const candidateBaseIndex = (activeBaseIndex + direction * step + length) % length;
      const candidate = normalizeUtilitySlot(candidateBaseIndex);
      const candidateItem = visibleUtilityItems[candidate];
      const candidateEl = utilityItemRefs.current[candidate];
      if (candidateItem?.safe && candidateEl && candidateEl.getAttribute('aria-disabled') !== 'true') {
        nextIndex = candidate;
        break;
      }
    }

    if (nextIndex !== activeUtilitySlotRef.current) {
      const nextItem = visibleUtilityItems[nextIndex];
      activeUtilitySlotRef.current = nextIndex;
      setActiveUtilitySlot(nextIndex);
      centerUtilitySlot(nextIndex, 'auto');
      window.requestAnimationFrame(() => {
        window.requestAnimationFrame(() => updateUtilitySelectionFromScroll(false));
      });
      if (!nextItem?.safe) return;
    }
  }, [centerUtilitySlot, normalizeUtilitySlot, updateUtilitySelectionFromScroll, utilityLoopOffset, visibleUtilityItems]);

  useEffect(() => {
    updateScrollState();
    window.addEventListener('scroll', updateScrollState, { passive: true });
    window.addEventListener('resize', updateScrollState);
    return () => {
      window.removeEventListener('scroll', updateScrollState);
      window.removeEventListener('resize', updateScrollState);
    };
  }, [updateScrollState]);

  useEffect(
    () => () => {
      if (movementClickTimer.current) {
        window.clearTimeout(movementClickTimer.current);
      }
      if (utilityScrollFrame.current) {
        window.cancelAnimationFrame(utilityScrollFrame.current);
      }
      if (utilitySnapTimer.current) {
        window.clearTimeout(utilitySnapTimer.current);
      }
    },
    []
  );

  useEffect(() => {
    const scrollEl = utilityScrollRef.current;
    if (!isRightOpen || !scrollEl) return undefined;

    centerUtilitySlot(activeUtilitySlotRef.current, 'auto');
    updateUtilitySelectionFromScroll();
    const handleUtilityScroll = () => updateUtilitySelectionFromScroll(true);
    scrollEl.addEventListener('scroll', handleUtilityScroll, { passive: true });
    scrollEl.addEventListener('wheel', handleUtilityWheel, { passive: false });
    window.addEventListener('resize', updateUtilitySelectionFromScroll);

    return () => {
      scrollEl.removeEventListener('scroll', handleUtilityScroll);
      scrollEl.removeEventListener('wheel', handleUtilityWheel);
      window.removeEventListener('resize', updateUtilitySelectionFromScroll);
      if (utilityScrollFrame.current) {
        window.cancelAnimationFrame(utilityScrollFrame.current);
        utilityScrollFrame.current = null;
      }
    };
  }, [centerUtilitySlot, handleUtilityWheel, isRightOpen, updateUtilitySelectionFromScroll]);

  useEffect(() => {
    const menu = leftMenuRef.current;
    if (!menu) return;
    if (!isLeftOpen) {
      menu.style.removeProperty('top');
      menu.style.removeProperty('left');
      menu.style.removeProperty('width');
      menu.style.removeProperty('max-height');
      menu.style.removeProperty('transform');
      return;
    }
    menu.style.setProperty('top', 'var(--left-menu-top)', 'important');
    menu.style.setProperty('left', 'var(--left-menu-edge)', 'important');
    menu.style.setProperty('width', 'min(var(--left-menu-width), calc(100vw - (var(--left-menu-edge) * 2)))', 'important');
    menu.style.setProperty('max-height', 'min(620px, calc(100vh - var(--left-menu-top) - var(--left-menu-bottom-gap)))', 'important');
    menu.style.setProperty('transform', 'translate3d(0, 0, 0)', 'important');
  }, [isLeftOpen]);

  useEffect(() => {
    const handleKeyDown = (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setIsCommandPaletteOpen((open) => !open);
      }
      if (event.key === 'Escape') {
        setIsCommandPaletteOpen(false);
        setIsLeftOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const goToSection = useCallback(
    (id) => {
      const item = sectionItems.find((candidate) => candidate.id === id) || sectionItems[0];
      const itemIndex = sectionItems.findIndex((candidate) => candidate.id === item.id);
      movementTargetIndexRef.current = Math.max(0, itemIndex);
      movementScrollLockUntilRef.current = Date.now() + 2200;
      setActiveSection(item.id);
      setIsLeftOpen(false);
      setIsCommandPaletteOpen(false);

      if (item.id === 'home' || item.id === 'features') {
        onNavigate(item.id);
      }

      const section = findSection(item);
      if (section) {
        section.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
      window.setTimeout(updateScrollState, 420);
    },
    [onNavigate, updateScrollState]
  );

  const currentSectionIndex = useCallback(() => {
    if (typeof window === 'undefined') {
      return Math.max(0, sectionItems.findIndex((item) => item.id === activeSection));
    }
    const viewportAnchor = window.scrollY + Math.max(96, window.innerHeight * 0.34);
    const sections = getSectionElements();
    if (!sections.length) {
      return Math.max(0, sectionItems.findIndex((item) => item.id === activeSection));
    }
    let currentId = sections[0].item.id;
    sections.forEach(({ item, element }) => {
      const top = element.getBoundingClientRect().top + window.scrollY;
      if (top <= viewportAnchor) {
        currentId = item.id;
      }
    });
    return Math.max(0, sectionItems.findIndex((item) => item.id === currentId));
  }, [activeSection]);

  const moveSection = (direction) => {
    const index = movementTargetIndexRef.current >= 0
      ? movementTargetIndexRef.current
      : currentSectionIndex();
    const nextIndex = Math.min(sectionItems.length - 1, Math.max(0, index + direction));
    movementTargetIndexRef.current = nextIndex;
    goToSection(sectionItems[nextIndex].id);
  };

  const forceScrollToDocumentEdge = (top) => {
    if (typeof window === 'undefined' || typeof document === 'undefined') return;
    const resolveTarget = () => {
      const root = document.documentElement;
      const body = document.body;
      const scrollHeight = Math.max(root.scrollHeight, body?.scrollHeight || 0);
      return top ? 0 : Math.max(0, scrollHeight - window.innerHeight);
    };
    const jump = () => {
      const target = resolveTarget();
      window.scrollTo(0, target);
      [document.scrollingElement, document.documentElement, document.body]
        .filter(Boolean)
        .forEach((element) => {
          element.scrollTop = target;
        });
    };

    jump();
    window.requestAnimationFrame(jump);
    window.setTimeout(jump, 120);
    window.setTimeout(jump, 260);
    window.setTimeout(jump, 620);
    window.setTimeout(jump, 960);
    window.setTimeout(() => {
      jump();
      updateScrollState();
    }, 1180);
  };

  const scrollToEdge = (top) => {
    const target = top ? sectionItems[0] : sectionItems[sectionItems.length - 1];
    movementTargetIndexRef.current = top ? 0 : sectionItems.length - 1;
    setActiveSection(target.id);
    setIsLeftOpen(false);
    setIsCommandPaletteOpen(false);
    if (target.id === 'home' || target.id === 'features') {
      onNavigate(target.id);
    }
    forceScrollToDocumentEdge(top);
  };

  const handleMovementClick = (direction) => {
    if (movementClickTimer.current) {
      window.clearTimeout(movementClickTimer.current);
      movementClickTimer.current = null;
    }
    lastMovementClick.current = { direction, time: Date.now() };
    moveSection(direction);
  };

  const handleMovementDoubleClick = (direction, event) => {
    event.preventDefault();
    if (movementClickTimer.current) {
      window.clearTimeout(movementClickTimer.current);
      movementClickTimer.current = null;
    }
    lastMovementClick.current = { direction, time: Date.now() };
    scrollToEdge(direction < 0);
  };

  const handleUtilitySelect = (index, item) => {
    const normalizedIndex = normalizeUtilitySlot(index);
    const selectedEl = utilityItemRefs.current[normalizedIndex];
    const scrollEl = utilityScrollRef.current;
    activeUtilitySlotRef.current = normalizedIndex;
    setActiveUtilitySlot(normalizedIndex);

    if (selectedEl && scrollEl) {
      const iconEl = selectedEl.querySelector('svg');
      const scrollRect = scrollEl.getBoundingClientRect();
      const iconRect = iconEl ? iconEl.getBoundingClientRect() : null;
      const iconTop = iconRect
        ? iconRect.top - scrollRect.top + scrollEl.scrollTop
        : selectedEl.offsetTop + Math.max(0, (selectedEl.offsetHeight - 26) / 2);
      const iconLeft = iconRect
        ? iconRect.left - scrollRect.left
        : selectedEl.offsetLeft + Math.max(0, (selectedEl.offsetWidth - 26) / 2);
      const iconHeight = iconRect ? iconRect.height : 26;
      const iconWidth = iconRect ? iconRect.width : 26;
      setUtilitySelectorStyle({
        top: `${iconTop + iconHeight / 2 - 32}px`,
        left: `${iconLeft + iconWidth / 2}px`,
        width: '64px',
        height: '64px',
      });
      centerUtilitySlot(normalizedIndex, 'smooth');
      window.requestAnimationFrame(() => {
        window.requestAnimationFrame(() => updateUtilitySelectionFromScroll(false));
      });
    }

    if (!item.safe) return;
  };


  const activeIndex = Math.max(0, sectionItems.findIndex((item) => item.id === activeSection));
  const canMoveUp = scrollState.canAscend;
  const canMoveDown = activeIndex < sectionItems.length - 1 && scrollState.canDescend;

  return (
    <div
      className={`home-obsidian-nav-layer home-palette-${activeColorScheme.id}`}
      style={{
        '--obsidian-primary': activeColorScheme.primary,
        '--obsidian-accent': activeColorScheme.accent,
        '--obsidian-surface': activeColorScheme.surface,
      }}
      data-testid="base2-obsidian-navigation"
      data-active-palette={activeColorScheme.id}
    >
      {isLeftOpen ? (
        <button
          type="button"
          className="home-left-command-backdrop"
          aria-label="Dismiss Base2 command overlay"
          onClick={() => setIsLeftOpen(false)}
          data-testid="base2-left-menu-backdrop"
        />
      ) : null}

      <button
        type="button"
        className={`home-left-menu-toggle ${isLeftOpen ? 'is-open' : ''}`}
        onClick={() => setIsLeftOpen((open) => !open)}
        aria-label={isLeftOpen ? 'Close Base2 command menu' : 'Open Base2 command menu'}
        aria-expanded={isLeftOpen}
        data-testid="base2-left-menu-toggle"
      >
        <span className="home-left-menu-pulse" aria-hidden="true" />
        {isLeftOpen ? <ChevronLeft aria-hidden="true" /> : <ChevronRight aria-hidden="true" />}
      </button>

      <div
        className={`home-left-command-menu ${isLeftOpen ? 'is-open' : ''}`}
        ref={leftMenuRef}
        style={isLeftOpen ? {
          top: 'var(--left-menu-top)',
          left: 'var(--left-menu-edge)',
          width: 'min(var(--left-menu-width), calc(100vw - (var(--left-menu-edge) * 2)))',
          maxHeight: 'min(620px, calc(100vh - var(--left-menu-top) - var(--left-menu-bottom-gap)))',
          transform: 'translate3d(0, 0, 0)',
        } : undefined}
        data-testid="base2-left-command-menu"
        aria-hidden={!isLeftOpen}
      >
        <div className="home-left-command-mark">
          <LayoutGrid aria-hidden="true" />
        </div>
        <div className="home-left-command-title">
          <div>
            <span>Base2</span>
            <strong>Command</strong>
          </div>
          <button
            type="button"
            className="home-left-command-close"
            onClick={() => setIsLeftOpen(false)}
            aria-label="Collapse Base2 command panel"
            tabIndex={isLeftOpen ? 0 : -1}
            data-testid="base2-left-menu-close"
          >
            <ChevronLeft aria-hidden="true" />
          </button>
        </div>
        <nav aria-label="Base2 page sections" className="home-left-command-list">
          {sectionItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeSection === item.id;
            return (
              <button
                type="button"
                key={item.id}
                onClick={() => goToSection(item.id)}
                className={isActive ? 'is-active' : ''}
                aria-current={isActive ? 'location' : undefined}
                tabIndex={isLeftOpen ? 0 : -1}
                data-testid={`base2-section-nav-${item.id}`}
              >
                <Icon aria-hidden="true" />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
        <div className="home-left-command-switches">
          <label>
            <span>
              <Activity aria-hidden="true" /> Pulse Guide
            </span>
            <input type="checkbox" checked readOnly aria-label="Pulse guide enabled" tabIndex={isLeftOpen ? 0 : -1} />
          </label>
          <label>
            <span>
              <LockKeyhole aria-hidden="true" /> Nav Buttons
            </span>
            <input
              type="checkbox"
              checked={navButtonsEnabled}
              onChange={() => setNavButtonsEnabled((enabled) => !enabled)}
              aria-label="Toggle Base2 movement buttons"
              tabIndex={isLeftOpen ? 0 : -1}
            />
          </label>
        </div>
        <button
          type="button"
          className="home-command-palette-open"
          onClick={() => setIsCommandPaletteOpen(true)}
          tabIndex={isLeftOpen ? 0 : -1}
          data-testid="base2-command-palette-open"
        >
          <Command aria-hidden="true" />
          <span>Command palette</span>
          <kbd>Ctrl K</kbd>
        </button>
      </div>

      {isCommandPaletteOpen ? (
        <div
          className="home-command-palette-modal"
          role="dialog"
          aria-modal="true"
          aria-label="Base2 command palette"
          data-testid="base2-command-palette"
        >
          <button
            type="button"
            className="home-command-palette-backdrop"
            aria-label="Close Base2 command palette"
            onClick={() => setIsCommandPaletteOpen(false)}
          />
          <div className="home-command-palette-surface">
            <div className="home-command-search-row">
              <Search aria-hidden="true" />
              <span>Search Base2 actions</span>
              <kbd>Esc</kbd>
            </div>
            <div className="home-command-palette-actions" role="menu">
              <div className="home-command-palette-schemes" role="group" aria-label="Base2 color schemes">
                {colorSchemes.map((scheme) => (
                  <button
                    type="button"
                    key={scheme.id}
                    className={scheme.id === colorSchemeId ? 'is-active' : ''}
                    onClick={() => setColorSchemeId(scheme.id)}
                    aria-pressed={scheme.id === colorSchemeId}
                    aria-label={`Use ${scheme.label} color scheme`}
                    data-testid={`base2-color-scheme-${scheme.id}`}
                    style={{
                      '--scheme-primary': scheme.primary,
                      '--scheme-accent': scheme.accent,
                    }}
                  >
                    <span>{scheme.label}</span>
                    <em>{scheme.id === colorSchemeId ? 'Active' : 'Apply'}</em>
                  </button>
                ))}
              </div>
              {commandActions.map((action) => (
                <button
                  type="button"
                  key={action.id}
                  role="menuitem"
                  disabled={!action.safe}
                  onClick={() => action.safe && goToSection(action.sectionId)}
                  aria-label={`${action.label}${action.safe ? '' : ' unavailable on public site'}`}
                >
                  <span>{action.label}</span>
                  <em>{action.safe ? 'Public safe' : 'Locked'}</em>
                </button>
              ))}
            </div>
          </div>
        </div>
      ) : null}

      <div
        className={`home-right-utility-menu ${isRightOpen ? 'is-open' : ''}`}
        data-testid="base2-right-utility-menu"
      >
        {isRightOpen ? (
          <div className="home-right-utility-panel" data-testid="base2-right-utility-icons">
            <div className="home-right-utility-nav-toggle">
              <span>Navigation</span>
              <button
                type="button"
                onClick={() => setNavButtonsEnabled((enabled) => !enabled)}
                aria-label="Toggle Base2 movement buttons"
                aria-pressed={navButtonsEnabled}
              >
                <span className={navButtonsEnabled ? 'is-on' : ''} />
              </button>
            </div>
            <div
              className="home-right-utility-scroll"
              role="listbox"
              aria-label="Base2 utility shortcuts"
              ref={utilityScrollRef}
              onScroll={updateUtilitySelectionFromScroll}
              style={{
                '--utility-selected-offset': utilitySelectorStyle.top,
                '--utility-selected-left': utilitySelectorStyle.left,
                '--utility-selected-width': utilitySelectorStyle.width,
                '--utility-selected-height': utilitySelectorStyle.height,
              }}
              data-testid="base2-right-utility-scroll"
            >
              {visibleUtilityItems.map((item, index) => {
                const Icon = item.icon;
                const isSelected = index === activeUtilitySlot;
                return (
                  <button
                    type="button"
                    className={`home-right-utility-icon ${isSelected ? 'is-active' : ''} ${item.safe ? '' : 'is-locked'}`}
                    role="option"
                    aria-label={`Base2 utility: ${item.label}${item.safe ? '' : ' unavailable on public site'}`}
                    aria-selected={isSelected}
                    aria-disabled={!item.safe}
                    ref={(node) => {
                      utilityItemRefs.current[index] = node;
                    }}
                    key={`${item.label}-${index}`}
                    onClick={() => handleUtilitySelect(index, item)}
                    title={`${item.label}${item.safe ? '' : ' locked'}`}
                  >
                    <Icon aria-hidden="true" />
                    <span>{item.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        ) : null}

        <button
          type="button"
          className="home-right-utility-toggle"
          onClick={() => setIsRightOpen((open) => !open)}
          aria-label={isRightOpen ? 'Close Base2 utility menu' : 'Open Base2 utility menu'}
          aria-expanded={isRightOpen}
          data-testid="base2-right-utility-toggle"
        >
          <ChevronLeft aria-hidden="true" />
        </button>
      </div>

      {navButtonsEnabled ? (
        <div className="home-bottom-movement-controls" data-testid="base2-bottom-movement-controls" data-active-section={activeSection}>
          <output className="home-active-section-output" data-testid="base2-section-active">
            {activeSection}
          </output>
          {canMoveUp ? (
            <button
              type="button"
              className="home-movement-button home-movement-button-up"
              onClick={() => handleMovementClick(-1)}
              onDoubleClick={(event) => handleMovementDoubleClick(-1, event)}
              aria-label="Scroll up to previous Base2 section"
              data-testid="base2-scroll-ascend"
            >
              <span className="home-movement-progress" style={{ height: `${scrollState.progress}%` }} />
              <ChevronUp aria-hidden="true" />
              <ArrowUp aria-hidden="true" />
            </button>
          ) : null}

          <button
            type="button"
            className="home-movement-button home-movement-button-down"
            onClick={() => handleMovementClick(1)}
            onDoubleClick={(event) => handleMovementDoubleClick(1, event)}
            aria-label="Scroll down to next Base2 section"
            disabled={!canMoveDown}
            data-testid="base2-scroll-descend"
          >
            <span className="home-movement-progress" style={{ height: `${scrollState.progress}%` }} />
            <ArrowDown aria-hidden="true" />
            <ChevronDown aria-hidden="true" />
          </button>
        </div>
      ) : null}
    </div>
  );
};

export default HomeObsidianNavigation;
