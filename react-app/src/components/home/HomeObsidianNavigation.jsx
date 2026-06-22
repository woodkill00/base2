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

const MOVEMENT_CLICK_DELAY_MS = 180;
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
  const utilityScrollRef = useRef(null);
  const utilityItemRefs = useRef([]);
  const utilityScrollFrame = useRef(null);
  const utilitySnapTimer = useRef(null);
  const activeUtilitySlotRef = useRef(activeUtilitySlot);

  const visibleUtilityItems = useMemo(
    () => [...utilityItems, ...utilityItems, ...utilityItems],
    []
  );
  const activeColorScheme = colorSchemes.find((scheme) => scheme.id === colorSchemeId) || colorSchemes[0];

  const updateScrollState = useCallback(() => {
    setScrollState(getScrollMetrics());
    setActiveSection(readActiveSection());
  }, []);

  useEffect(() => {
    activeUtilitySlotRef.current = activeUtilitySlot;
  }, [activeUtilitySlot]);

  const centerUtilitySlot = useCallback((index, behavior = 'auto') => {
    const scrollEl = utilityScrollRef.current;
    const selectedEl = utilityItemRefs.current[index];
    if (!scrollEl || !selectedEl) return;

    const iconEl = selectedEl.querySelector('svg');
    const itemCenter = iconEl
      ? selectedEl.offsetTop + iconEl.offsetTop + iconEl.offsetHeight / 2
      : selectedEl.offsetTop + selectedEl.offsetHeight / 2;
    scrollEl.scrollTo({
      top: Math.max(0, itemCenter - scrollEl.clientHeight / 2),
      behavior,
    });
  }, []);

  const updateUtilitySelectionFromScroll = useCallback((shouldSettle = false) => {
    const scrollEl = utilityScrollRef.current;
    if (!scrollEl || typeof window === 'undefined') return;

    if (utilityScrollFrame.current) {
      window.cancelAnimationFrame(utilityScrollFrame.current);
    }

    utilityScrollFrame.current = window.requestAnimationFrame(() => {
      utilityScrollFrame.current = null;
      const viewportCenter = scrollEl.scrollTop + scrollEl.clientHeight / 2;
      let nextSlot = activeUtilitySlotRef.current;
      let nearestDistance = Number.POSITIVE_INFINITY;

      utilityItemRefs.current.forEach((itemEl, index) => {
        if (!itemEl) return;
        if (itemEl.getAttribute('aria-disabled') === 'true' || itemEl.classList.contains('is-locked')) return;
        const itemIcon = itemEl.querySelector('svg');
        const itemCenter = itemIcon
          ? itemEl.offsetTop + itemIcon.offsetTop + itemIcon.offsetHeight / 2
          : itemEl.offsetTop + itemEl.offsetHeight / 2;
        const distance = Math.abs(itemCenter - viewportCenter);
        if (distance < nearestDistance) {
          nearestDistance = distance;
          nextSlot = index;
        }
      });

      const selectedEl = utilityItemRefs.current[nextSlot];
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
      activeUtilitySlotRef.current = nextSlot;
      setActiveUtilitySlot(nextSlot);
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
          centerUtilitySlot(nextSlot, 'smooth');
        }, 120);
      }
    });
  }, [centerUtilitySlot]);

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
    window.addEventListener('resize', updateUtilitySelectionFromScroll);

    return () => {
      scrollEl.removeEventListener('scroll', handleUtilityScroll);
      window.removeEventListener('resize', updateUtilitySelectionFromScroll);
      if (utilityScrollFrame.current) {
        window.cancelAnimationFrame(utilityScrollFrame.current);
        utilityScrollFrame.current = null;
      }
    };
  }, [centerUtilitySlot, isRightOpen, updateUtilitySelectionFromScroll]);

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

  const moveSection = (direction) => {
    const index = Math.max(0, sectionItems.findIndex((item) => item.id === activeSection));
    const nextIndex = Math.min(sectionItems.length - 1, Math.max(0, index + direction));
    goToSection(sectionItems[nextIndex].id);
  };

  const scrollToEdge = (top) => {
    const target = top ? sectionItems[0] : sectionItems[sectionItems.length - 1];
    goToSection(target.id);
  };

  const handleMovementClick = (direction, event) => {
    if (movementClickTimer.current) {
      window.clearTimeout(movementClickTimer.current);
      movementClickTimer.current = null;
    }
    if (event.detail >= 2) {
      scrollToEdge(direction < 0);
      return;
    }
    movementClickTimer.current = window.setTimeout(() => {
      movementClickTimer.current = null;
      moveSection(direction);
    }, MOVEMENT_CLICK_DELAY_MS);
  };

  const handleUtilitySelect = (index, item) => {
    const selectedEl = utilityItemRefs.current[index];
    const scrollEl = utilityScrollRef.current;
    activeUtilitySlotRef.current = index;
    setActiveUtilitySlot(index);

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
      centerUtilitySlot(index, 'smooth');
      window.requestAnimationFrame(() => {
        window.requestAnimationFrame(() => updateUtilitySelectionFromScroll(false));
      });
    }

    if (!item.safe) return;
  };

  const handleUtilityWheel = (event) => {
    if (event.cancelable) {
      event.preventDefault();
    }
    const direction = event.deltaY >= 0 ? 1 : -1;
    let nextIndex = activeUtilitySlotRef.current;

    for (let step = 1; step < visibleUtilityItems.length; step += 1) {
      const candidate = activeUtilitySlotRef.current + direction * step;
      if (candidate < 0 || candidate >= visibleUtilityItems.length) break;
      const candidateItem = visibleUtilityItems[candidate];
      const candidateEl = utilityItemRefs.current[candidate];
      if (candidateItem?.safe && candidateEl && candidateEl.getAttribute('aria-disabled') !== 'true') {
        nextIndex = candidate;
        break;
      }
    }

    if (nextIndex !== activeUtilitySlotRef.current) {
      handleUtilitySelect(nextIndex, visibleUtilityItems[nextIndex]);
    }
  };

  const activeIndex = Math.max(0, sectionItems.findIndex((item) => item.id === activeSection));
  const canMoveUp = activeIndex > 0 && scrollState.canAscend;
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
              onWheel={handleUtilityWheel}
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
          <button
            type="button"
            className="home-movement-button home-movement-button-up"
            onClick={(event) => handleMovementClick(-1, event)}
            aria-label="Scroll up to previous Base2 section"
            disabled={!canMoveUp}
            data-testid="base2-scroll-ascend"
          >
            <span className="home-movement-progress" style={{ height: `${scrollState.progress}%` }} />
            <ChevronUp aria-hidden="true" />
            <ArrowUp aria-hidden="true" />
          </button>

          <button
            type="button"
            className="home-movement-button home-movement-button-down"
            onClick={(event) => handleMovementClick(1, event)}
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
