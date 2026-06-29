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
  return document.getElementById(item.target) || document.querySelector(`[data-testid="${item.target}"]`);
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

const clampScrollTarget = (target) => {
  if (typeof window === 'undefined' || typeof document === 'undefined') return 0;
  const root = document.documentElement;
  const body = document.body;
  const scrollRoot = document.scrollingElement || root;
  const scrollHeight = Math.max(root.scrollHeight, body?.scrollHeight || 0, scrollRoot?.scrollHeight || 0);
  const maxScroll = Math.max(0, scrollHeight - window.innerHeight);
  return Math.min(maxScroll, Math.max(0, Math.round(target)));
};

const getSnapStopElements = () => {
  if (typeof document === 'undefined' || typeof window === 'undefined') return [];
  const selectors = [
    '[data-testid="base2-preserved-home-hero"]',
    '#features',
    '[data-base2-section-panel]',
    'main > section',
    'main > footer',
    'main > [data-testid]',
    '#home-page > section',
    '#home-page > footer',
    '#home-page > [data-testid]',
  ];
  const seen = new Set();
  return selectors.flatMap((selector) => Array.from(document.querySelectorAll(selector))).filter((element) => {
    if (seen.has(element)) return false;
    seen.add(element);
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return style.display !== 'none'
      && style.visibility !== 'hidden'
      && rect.width >= Math.min(280, window.innerWidth * 0.6)
      && rect.height >= Math.min(180, window.innerHeight * 0.24);
  });
};

const getMovementStops = () => {
  if (typeof window === 'undefined' || typeof document === 'undefined') return [0];
  const root = document.documentElement;
  const body = document.body;
  const scrollRoot = document.scrollingElement || root;
  const scrollHeight = Math.max(root.scrollHeight, body?.scrollHeight || 0, scrollRoot?.scrollHeight || 0);
  const maxScroll = Math.max(0, scrollHeight - window.innerHeight);
  const elementStops = getSnapStopElements()
    .map((element) => element.getBoundingClientRect().top + window.scrollY)
    .map((top) => clampScrollTarget(top));
  const viewportStops = Array.from(
    { length: Math.ceil(maxScroll / Math.max(1, window.innerHeight)) + 1 },
    (_, index) => clampScrollTarget(index * window.innerHeight)
  );
  const sourceStops = elementStops.length >= 4 ? elementStops : viewportStops;
  const duplicateTopTolerance = Math.max(72, Math.round(window.innerHeight * 0.1));
  const stops = [0, ...sourceStops, maxScroll]
    .map((stop) => (stop <= duplicateTopTolerance ? 0 : stop))
    .sort((a, b) => a - b);
  return stops.filter((value, index) => index === 0 || Math.abs(value - stops[index - 1]) > 24);
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
  const [activeLeftSectionSlot, setActiveLeftSectionSlot] = useState(sectionItems.length);
  const [activeUtilitySlot, setActiveUtilitySlot] = useState(utilityItems.length + 4);
  const [utilitySelectorStyle, setUtilitySelectorStyle] = useState(UTILITY_SELECTOR_FALLBACK);
  const [colorSchemeId, setColorSchemeId] = useState('volcanic');
  const [scrollState, setScrollState] = useState(getScrollMetrics);
  const movementClickTimer = useRef(null);
  const lastMovementClick = useRef({ direction: 0, time: 0 });
  const leftToggleRef = useRef(null);
  const leftMenuRef = useRef(null);
  const leftSectionListRef = useRef(null);
  const leftSectionButtonRefs = useRef([]);
  const leftSectionSnapTimer = useRef(null);
  const leftSectionWheelLockUntilRef = useRef(0);
  const activeLeftSectionSlotRef = useRef(sectionItems.length);
  const utilityScrollRef = useRef(null);
  const utilityItemRefs = useRef([]);
  const utilityScrollFrame = useRef(null);
  const utilitySnapTimer = useRef(null);
  const activeUtilitySlotRef = useRef(activeUtilitySlot);
  const movementScrollLockUntilRef = useRef(0);
  const movementAlignTimers = useRef([]);

  const visibleSectionItems = useMemo(
    () => [...sectionItems, ...sectionItems, ...sectionItems],
    []
  );
  const sectionLoopOffset = sectionItems.length;
  const normalizeSectionSlot = useCallback((index) => {
    const length = sectionItems.length;
    return sectionLoopOffset + ((index % length) + length) % length;
  }, [sectionLoopOffset]);

  const centerLeftSectionSlot = useCallback((index, smooth = true) => {
    const scrollEl = leftSectionListRef.current;
    const target = leftSectionButtonRefs.current[index];
    if (!scrollEl || !target) return;
    const targetTop = target.offsetTop - (scrollEl.clientHeight / 2) + (target.offsetHeight / 2);
    if (typeof scrollEl.scrollTo === 'function') {
      scrollEl.scrollTo({ top: targetTop, behavior: smooth ? 'smooth' : 'auto' });
    } else {
      scrollEl.scrollTop = targetTop;
    }
  }, []);

  const updateActiveLeftSectionFromScroll = useCallback((snap = false) => {
    const scrollEl = leftSectionListRef.current;
    if (!scrollEl) return;
    const centerY = scrollEl.scrollTop + scrollEl.clientHeight / 2;
    const buttons = leftSectionButtonRefs.current.filter(Boolean);
    if (!buttons.length) return;
    let closestIndex = 0;
    let closestDistance = Number.POSITIVE_INFINITY;
    buttons.forEach((button, index) => {
      const buttonCenter = button.offsetTop + button.offsetHeight / 2;
      const distance = Math.abs(buttonCenter - centerY);
      if (distance < closestDistance) {
        closestDistance = distance;
        closestIndex = index;
      }
    });
    const item = visibleSectionItems[closestIndex];
    const canonicalIndex = normalizeSectionSlot(closestIndex);
    activeLeftSectionSlotRef.current = canonicalIndex;
    setActiveLeftSectionSlot(canonicalIndex);
    if (item && item.id !== activeSection) {
      setActiveSection(item.id);
    }
    if (snap) {
      centerLeftSectionSlot(canonicalIndex, true);
    }
  }, [activeSection, centerLeftSectionSlot, normalizeSectionSlot, visibleSectionItems]);

  const moveLeftSectionSlot = useCallback((index, smooth = false) => {
    const nextSlot = normalizeSectionSlot(index);
    const nextItem = visibleSectionItems[nextSlot];
    if (nextItem) {
      activeLeftSectionSlotRef.current = nextSlot;
      setActiveSection(nextItem.id);
      setActiveLeftSectionSlot(nextSlot);
    }
    leftSectionWheelLockUntilRef.current = Date.now() + 360;
    centerLeftSectionSlot(nextSlot, smooth);
    window.clearTimeout(leftSectionSnapTimer.current);
    leftSectionSnapTimer.current = window.setTimeout(() => updateActiveLeftSectionFromScroll(true), 220);
  }, [centerLeftSectionSlot, normalizeSectionSlot, updateActiveLeftSectionFromScroll, visibleSectionItems]);

  const handleLeftSectionWheel = useCallback((event) => {
    const node = event.currentTarget || leftSectionListRef.current;
    const buttons = leftSectionButtonRefs.current.filter(Boolean);
    const maxScroll = Math.max(0, node.scrollHeight - node.clientHeight);
    if (maxScroll <= 2 || !buttons.length) return;
    event.preventDefault();

    const direction = event.deltaY >= 0 ? 1 : -1;
    const edge = Math.max(4, Math.min(24, node.clientHeight * 0.08));
    const currentSlot = normalizeSectionSlot(activeLeftSectionSlotRef.current);
    const nextSlot = direction > 0 && node.scrollTop >= maxScroll - edge
      ? normalizeSectionSlot(0)
      : direction < 0 && node.scrollTop <= edge
        ? normalizeSectionSlot(sectionItems.length - 1)
        : normalizeSectionSlot(currentSlot + direction);
    moveLeftSectionSlot(nextSlot, false);
  }, [moveLeftSectionSlot, normalizeSectionSlot]);

  const handleLeftSectionScroll = useCallback(() => {
    if (Date.now() < leftSectionWheelLockUntilRef.current) return;
    updateActiveLeftSectionFromScroll(false);
    window.clearTimeout(leftSectionSnapTimer.current);
    leftSectionSnapTimer.current = window.setTimeout(() => updateActiveLeftSectionFromScroll(true), 160);
  }, [updateActiveLeftSectionFromScroll]);

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

  const clearMovementAlignTimers = useCallback(() => {
    movementAlignTimers.current.forEach(({ type, id }) => {
      if (type === 'interval') {
        window.clearInterval(id);
      } else {
        window.clearTimeout(id);
      }
    });
    movementAlignTimers.current = [];
  }, []);

  const scheduleMovementTimeout = useCallback((callback, delay) => {
    const id = window.setTimeout(() => {
      movementAlignTimers.current = movementAlignTimers.current.filter((timer) => timer.id !== id);
      callback();
    }, delay);
    movementAlignTimers.current.push({ type: 'timeout', id });
    return id;
  }, []);

  const scheduleMovementInterval = useCallback((callback, delay) => {
    const id = window.setInterval(callback, delay);
    movementAlignTimers.current.push({ type: 'interval', id });
    return id;
  }, []);

  const updateScrollState = useCallback(() => {
    setScrollState(getScrollMetrics());
    const nextActiveSection = readActiveSection();
    if (Date.now() > movementScrollLockUntilRef.current) {
      setActiveSection(nextActiveSection);
    }
  }, []);

  useEffect(() => {
    activeUtilitySlotRef.current = activeUtilitySlot;
  }, [activeUtilitySlot]);

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
    const targetTop = Math.max(0, itemCenter - scrollEl.clientHeight / 2);
    if (typeof scrollEl.scrollTo === 'function') {
      scrollEl.scrollTo({ top: targetTop, behavior });
    } else {
      scrollEl.scrollTop = targetTop;
    }
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
      menu.style.removeProperty('height');
      menu.style.removeProperty('max-height');
      menu.style.removeProperty('transform');
      return;
    }
    menu.style.setProperty('top', 'var(--left-menu-top)', 'important');
    menu.style.setProperty('left', 'var(--left-menu-edge)', 'important');
    menu.style.setProperty('width', 'min(var(--left-menu-width), calc(100vw - (var(--left-menu-edge) * 2)))', 'important');
    menu.style.setProperty('height', 'min(90dvh, var(--left-menu-safe-height))', 'important');
    menu.style.setProperty('max-height', 'min(90dvh, var(--left-menu-safe-height))', 'important');
    menu.style.setProperty('transform', 'translate3d(0, 0, 0)', 'important');
  }, [isLeftOpen]);

  useEffect(() => {
    if (!isLeftOpen) return;
    const scrollEl = leftSectionListRef.current;
    const activeIndex = sectionItems.findIndex((item) => item.id === activeSection);
    const normalizedIndex = normalizeSectionSlot(Math.max(0, activeIndex));
    const selectedEl = leftSectionButtonRefs.current[normalizedIndex];
    if (!scrollEl || !selectedEl) return;
    activeLeftSectionSlotRef.current = normalizedIndex;
    setActiveLeftSectionSlot(normalizedIndex);
    const itemCenter = selectedEl.offsetTop + selectedEl.offsetHeight / 2;
    const targetTop = Math.max(0, itemCenter - scrollEl.clientHeight / 2);
    if (typeof scrollEl.scrollTo === 'function') {
      scrollEl.scrollTo({ top: targetTop, behavior: 'auto' });
    } else {
      scrollEl.scrollTop = targetTop;
    }
  }, [activeSection, isLeftOpen, normalizeSectionSlot]);

  useEffect(() => {
    const scrollEl = leftSectionListRef.current;
    if (!isLeftOpen || !scrollEl) return undefined;
    scrollEl.addEventListener('wheel', handleLeftSectionWheel, { passive: false });
    return () => {
      scrollEl.removeEventListener('wheel', handleLeftSectionWheel);
    };
  }, [handleLeftSectionWheel, isLeftOpen]);

  useEffect(() => {
    if (isLeftOpen) return;
    window.requestAnimationFrame(() => {
      if (document.activeElement === document.body || document.activeElement?.closest?.('[data-testid="base2-left-command-menu"]')) {
        leftToggleRef.current?.focus?.();
      }
    });
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

  const handleLeftSectionKeyDown = (event, index) => {
    const buttons = leftSectionButtonRefs.current.filter(Boolean);
    if (!buttons.length) return;
    if (event.key === 'ArrowDown' || event.key === 'ArrowRight') {
      event.preventDefault();
      buttons[(index + 1) % buttons.length]?.focus();
    }
    if (event.key === 'ArrowUp' || event.key === 'ArrowLeft') {
      event.preventDefault();
      buttons[(index - 1 + buttons.length) % buttons.length]?.focus();
    }
    if (event.key === 'Home') {
      event.preventDefault();
      buttons[0]?.focus();
    }
    if (event.key === 'End') {
      event.preventDefault();
      buttons[buttons.length - 1]?.focus();
    }
  };

  const forceSectionIntoView = useCallback((item) => {
    const section = findSection(item);
    if (!section || typeof window === 'undefined' || typeof document === 'undefined') return;
    clearMovementAlignTimers();
    const scrollToSectionTop = () => {
      const root = document.documentElement;
      const body = document.body;
      const scrollRoot = document.scrollingElement || root;
      const previousRootBehavior = root.style.scrollBehavior;
      const previousBodyBehavior = body.style.scrollBehavior;
      root.style.scrollBehavior = 'auto';
      body.style.scrollBehavior = 'auto';
      const scrollHeight = Math.max(root.scrollHeight, body?.scrollHeight || 0, scrollRoot?.scrollHeight || 0);
      const maxScroll = Math.max(0, scrollHeight - window.innerHeight);
      const currentScroll = window.scrollY || scrollRoot?.scrollTop || root.scrollTop || body.scrollTop || 0;
      const sectionTop = section.getBoundingClientRect().top + currentScroll;
      const targetTop = Math.min(Math.max(0, sectionTop), maxScroll);
      window.scrollTo({ top: targetTop, behavior: 'auto' });
      [scrollRoot, root, body]
        .filter(Boolean)
        .forEach((element) => {
          element.scrollTop = targetTop;
        });
      root.style.scrollBehavior = previousRootBehavior;
      body.style.scrollBehavior = previousBodyBehavior;
    };
    scrollToSectionTop();
    window.requestAnimationFrame(scrollToSectionTop);
    [120, 320, 720, 1240, 1880, 2600, 3600, 4600, 5600].forEach((delay) => {
      scheduleMovementTimeout(scrollToSectionTop, delay);
    });
    const startedAt = Date.now();
    let stableTicks = 0;
    const alignTimer = scheduleMovementInterval(() => {
      scrollToSectionTop();
      const rect = section.getBoundingClientRect();
      stableTicks = Math.abs(rect.top) <= 3 ? stableTicks + 1 : 0;
      if (stableTicks >= 8 || Date.now() - startedAt > 6800) {
        window.clearInterval(alignTimer);
        movementAlignTimers.current = movementAlignTimers.current.filter((timer) => timer.id !== alignTimer);
      }
    }, 180);
  }, [clearMovementAlignTimers, scheduleMovementInterval, scheduleMovementTimeout]);

  const goToSection = useCallback(
    (id) => {
      const item = sectionItems.find((candidate) => candidate.id === id) || sectionItems[0];
      movementScrollLockUntilRef.current = Date.now() + 7600;
      setActiveSection(item.id);
      setIsLeftOpen(false);
      setIsCommandPaletteOpen(false);

      if (item.id === 'home' || item.id === 'features') {
        onNavigate(item.id);
      }

      forceSectionIntoView(item);
      window.setTimeout(updateScrollState, 420);
      window.setTimeout(updateScrollState, 840);
    },
    [forceSectionIntoView, onNavigate, updateScrollState]
  );

  const moveSection = (direction) => {
    if (typeof window === 'undefined' || typeof document === 'undefined') return;
    clearMovementAlignTimers();
    const root = document.documentElement;
    const body = document.body;
    const scrollRoot = document.scrollingElement || root;
    const scrollHeight = Math.max(root.scrollHeight, body?.scrollHeight || 0, scrollRoot?.scrollHeight || 0);
    const maxScroll = Math.max(0, scrollHeight - window.innerHeight);
    const currentScroll = window.scrollY || scrollRoot?.scrollTop || root.scrollTop || body.scrollTop || 0;
    const stops = getMovementStops();
    const targetStop = direction > 0
      ? stops.find((stop) => stop > currentScroll + 24)
      : [...stops].reverse().find((stop) => stop < currentScroll - 24);
    const targetTop = typeof targetStop === 'number' ? targetStop : (direction > 0 ? maxScroll : 0);
    const jump = () => {
      const previousRootBehavior = root.style.scrollBehavior;
      const previousBodyBehavior = body?.style.scrollBehavior;
      root.style.scrollBehavior = 'auto';
      if (body) body.style.scrollBehavior = 'auto';
      window.scrollTo(0, targetTop);
      [document.scrollingElement, document.documentElement, document.body]
        .filter(Boolean)
        .forEach((element) => {
          element.scrollTop = targetTop;
        });
      root.style.scrollBehavior = previousRootBehavior;
      if (body) body.style.scrollBehavior = previousBodyBehavior;
    };
    movementScrollLockUntilRef.current = Date.now() + 760;
    jump();
    window.requestAnimationFrame(jump);
    [16, 50, 100, 180, 280, 420, 600].forEach((delay) => {
      scheduleMovementTimeout(jump, delay);
    });
    updateScrollState();
    window.requestAnimationFrame(updateScrollState);
    window.setTimeout(updateScrollState, 760);
  };

  const queueSingleMovement = (direction) => {
    if (movementClickTimer.current) {
      window.clearTimeout(movementClickTimer.current);
    }
    movementClickTimer.current = null;
    moveSection(direction);
  };

  const forceScrollToDocumentEdge = (top) => {
    if (typeof window === 'undefined' || typeof document === 'undefined') return;
    clearMovementAlignTimers();
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
    [120, 260, 620, 960, 1320, 1900, 2700, 3600, 4600, 5600].forEach((delay) => {
      scheduleMovementTimeout(jump, delay);
    });
    const startedAt = Date.now();
    let stableTicks = 0;
    const edgeTimer = scheduleMovementInterval(() => {
      jump();
      const target = resolveTarget();
      const current = window.scrollY || document.documentElement.scrollTop || 0;
      stableTicks = Math.abs(current - target) <= 3 ? stableTicks + 1 : 0;
      if (stableTicks >= 8 || Date.now() - startedAt > 6800) {
        window.clearInterval(edgeTimer);
        movementAlignTimers.current = movementAlignTimers.current.filter((timer) => timer.id !== edgeTimer);
      }
    }, 180);
    scheduleMovementTimeout(() => {
      jump();
      updateScrollState();
    }, 7000);
  };

  const scrollToEdge = (top) => {
    const target = top ? sectionItems[0] : sectionItems[sectionItems.length - 1];
    movementScrollLockUntilRef.current = Date.now() + 7600;
    setActiveSection(target.id);
    setIsLeftOpen(false);
    setIsCommandPaletteOpen(false);
    if (target.id === 'home' || target.id === 'features') {
      onNavigate(target.id);
    }
    forceScrollToDocumentEdge(top);
  };

  const handleMovementClick = (direction) => {
    lastMovementClick.current = { direction, time: Date.now() };
    queueSingleMovement(direction);
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


  const canMoveUp = scrollState.canAscend;
  const canMoveDown = scrollState.canDescend;

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
        ref={leftToggleRef}
        onClick={() => setIsLeftOpen((open) => !open)}
        aria-label={isLeftOpen ? 'Close Base2 command menu' : 'Open Base2 command menu'}
        aria-expanded={isLeftOpen}
        aria-controls="base2-left-command-menu"
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
          height: 'min(90dvh, var(--left-menu-safe-height))',
          maxHeight: 'min(90dvh, var(--left-menu-safe-height))',
          transform: 'translate3d(0, 0, 0)',
        } : undefined}
        data-testid="base2-left-command-menu"
        id="base2-left-command-menu"
        aria-hidden={!isLeftOpen}
        aria-labelledby="base2-left-command-title"
      >
        <div className="home-left-command-mark">
          <LayoutGrid aria-hidden="true" />
        </div>
        <div className="home-left-command-title" id="base2-left-command-title">
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
        <nav
          aria-label="Base2 page sections"
          className="home-left-command-list"
          ref={leftSectionListRef}
          data-testid="base2-left-section-list"
          onScroll={handleLeftSectionScroll}
        >
          {visibleSectionItems.map((item, index) => {
            const Icon = item.icon;
            const isCanonicalLoop = index >= sectionLoopOffset && index < sectionLoopOffset + sectionItems.length;
            const loopPosition = index < sectionLoopOffset ? 'previous' : (isCanonicalLoop ? 'middle' : 'next');
            const isLoopBoundary = index % sectionItems.length === 0;
            const isActive = index === activeLeftSectionSlot;
            return (
              <button
                type="button"
                key={`${item.id}-${index}`}
                ref={(node) => {
                  leftSectionButtonRefs.current[index] = node;
                }}
                onClick={() => goToSection(item.id)}
                onKeyDown={(event) => handleLeftSectionKeyDown(event, index)}
                className={isActive ? 'is-active' : ''}
                aria-current={isActive ? 'location' : undefined}
                tabIndex={isLeftOpen ? 0 : -1}
                data-section-loop={loopPosition}
                data-loop-boundary={isLoopBoundary ? 'start' : undefined}
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

          {canMoveDown ? (
            <button
              type="button"
              className="home-movement-button home-movement-button-down"
              onClick={() => handleMovementClick(1)}
              onDoubleClick={(event) => handleMovementDoubleClick(1, event)}
              aria-label="Scroll down to next Base2 section"
              data-testid="base2-scroll-descend"
            >
              <span className="home-movement-progress" style={{ height: `${scrollState.progress}%` }} />
              <ArrowDown aria-hidden="true" />
              <ChevronDown aria-hidden="true" />
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
};

export default HomeObsidianNavigation;
