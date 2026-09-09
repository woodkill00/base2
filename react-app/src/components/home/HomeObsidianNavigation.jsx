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
  { id: 'home', labelKey: 'home', target: 'home-page', icon: LayoutGrid },
  { id: 'features', labelKey: 'features', target: 'features', icon: Zap },
  { id: 'command', labelKey: 'command', target: 'base2-obsidian-ops', icon: Search },
  { id: 'security', labelKey: 'security', target: 'base2-thermal-security', icon: ShieldCheck },
  { id: 'contact', labelKey: 'contact', target: 'contact', icon: Server },
];

const utilityItems = [
  { labelKey: 'settings', icon: Settings, safe: false },
  { labelKey: 'notifications', icon: Bell, safe: false },
  { labelKey: 'share', icon: Share2, safe: true, action: 'share' },
  { labelKey: 'history', icon: History, safe: false },
  { labelKey: 'security', icon: Shield, safe: true, action: 'security' },
  { labelKey: 'automation', icon: Zap, safe: false },
  { labelKey: 'search', icon: Search, safe: true, action: 'search' },
  { labelKey: 'profile', icon: User, safe: false },
  { labelKey: 'favorites', icon: Heart, safe: false },
  { labelKey: 'signOut', icon: LogOut, safe: false },
];

const commandActions = [
  { id: 'go-home', labelKey: 'goHome', sectionId: 'home', safe: true },
  { id: 'go-features', labelKey: 'reviewFeatures', sectionId: 'features', safe: true },
  { id: 'go-command', labelKey: 'openCommand', sectionId: 'command', safe: true },
  { id: 'go-security', labelKey: 'inspectSecurity', sectionId: 'security', safe: true },
  { id: 'go-contact', labelKey: 'contactBase2', sectionId: 'contact', safe: true },
  { id: 'admin-debug', labelKey: 'adminDiagnostics', safe: false },
];

const navigationCopy = {
  en: {
    home: 'Home',
    features: 'Features',
    command: 'Command',
    security: 'Security',
    contact: 'Contact',
    settings: 'Settings',
    notifications: 'Notifications',
    share: 'Share',
    history: 'History',
    automation: 'Automation',
    search: 'Search',
    profile: 'Profile',
    favorites: 'Favorites',
    signOut: 'Sign out',
    goHome: 'Go to home',
    reviewFeatures: 'Review Base2 features',
    openCommand: 'Open command operations',
    inspectSecurity: 'Inspect security surface',
    contactBase2: 'Contact Base2',
    adminDiagnostics: 'Admin diagnostics',
    dismissOverlay: 'Dismiss Base2 command overlay',
    closeCommand: 'Close Base2 command menu',
    openCommandMenu: 'Open Base2 command menu',
    collapsePanel: 'Collapse Base2 command panel',
    pageSections: 'Base2 page sections',
    pulseGuide: 'Pulse Guide',
    pulseEnabled: 'Pulse guide enabled',
    navButtons: 'Nav Buttons',
    toggleMovement: 'Toggle Base2 movement buttons',
    commandPalette: 'Command palette',
    paletteLabel: 'Base2 command palette',
    closePalette: 'Close Base2 command palette',
    searchActions: 'Search Base2 actions',
    colorSchemes: 'Base2 color schemes',
    useScheme: 'Use',
    schemeSuffix: 'color scheme',
    active: 'Active',
    apply: 'Apply',
    unavailable: 'unavailable on public site',
    publicSafe: 'Public safe',
    locked: 'Locked',
    navigation: 'Navigation',
    utilityShortcuts: 'Base2 utility shortcuts',
    utilityPrefix: 'Base2 utility:',
    closeUtility: 'Close Base2 utility menu',
    openUtility: 'Open Base2 utility menu',
    scrollUp: 'Scroll up to previous Base2 section',
    scrollDown: 'Scroll down to next Base2 section',
  },
  de: {
    home: 'Start',
    features: 'Funktionen',
    command: 'Befehle',
    security: 'Sicherheit',
    contact: 'Kontakt',
    settings: 'Einstellungen',
    notifications: 'Benachrichtigungen',
    share: 'Teilen',
    history: 'Verlauf',
    automation: 'Automatisierung',
    search: 'Suche',
    profile: 'Profil',
    favorites: 'Favoriten',
    signOut: 'Abmelden',
    goHome: 'Zur Startseite',
    reviewFeatures: 'Base2-Funktionen ansehen',
    openCommand: 'Befehlsbetrieb öffnen',
    inspectSecurity: 'Sicherheitsbereich prüfen',
    contactBase2: 'Base2 kontaktieren',
    adminDiagnostics: 'Admin-Diagnose',
    dismissOverlay: 'Base2-Befehlsfenster schließen',
    closeCommand: 'Base2-Befehlsmenü schließen',
    openCommandMenu: 'Base2-Befehlsmenü öffnen',
    collapsePanel: 'Base2-Befehlsbereich einklappen',
    pageSections: 'Base2-Seitenbereiche',
    pulseGuide: 'Impulsführung',
    pulseEnabled: 'Impulsführung aktiviert',
    navButtons: 'Navigationstasten',
    toggleMovement: 'Base2-Navigationstasten umschalten',
    commandPalette: 'Befehlspalette',
    paletteLabel: 'Base2-Befehlspalette',
    closePalette: 'Base2-Befehlspalette schließen',
    searchActions: 'Base2-Aktionen durchsuchen',
    colorSchemes: 'Base2-Farbschemata',
    useScheme: 'Verwende',
    schemeSuffix: 'als Farbschema',
    active: 'Aktiv',
    apply: 'Anwenden',
    unavailable: 'auf der öffentlichen Seite nicht verfügbar',
    publicSafe: 'Öffentlich verfügbar',
    locked: 'Gesperrt',
    navigation: 'Navigation',
    utilityShortcuts: 'Base2-Schnellzugriffe',
    utilityPrefix: 'Base2-Schnellzugriff:',
    closeUtility: 'Base2-Schnellzugriffe schließen',
    openUtility: 'Base2-Schnellzugriffe öffnen',
    scrollUp: 'Zum vorherigen Base2-Bereich scrollen',
    scrollDown: 'Zum nächsten Base2-Bereich scrollen',
  },
  ar: {
    home: 'الرئيسية',
    features: 'الميزات',
    command: 'الأوامر',
    security: 'الأمان',
    contact: 'اتصل بنا',
    settings: 'الإعدادات',
    notifications: 'الإشعارات',
    share: 'مشاركة',
    history: 'السجل',
    automation: 'الأتمتة',
    search: 'بحث',
    profile: 'الملف الشخصي',
    favorites: 'المفضلة',
    signOut: 'تسجيل الخروج',
    goHome: 'الانتقال إلى الرئيسية',
    reviewFeatures: 'استعراض ميزات Base2',
    openCommand: 'فتح عمليات الأوامر',
    inspectSecurity: 'فحص واجهة الأمان',
    contactBase2: 'التواصل مع Base2',
    adminDiagnostics: 'تشخيص المسؤول',
    dismissOverlay: 'إغلاق طبقة أوامر Base2',
    closeCommand: 'إغلاق قائمة أوامر Base2',
    openCommandMenu: 'فتح قائمة أوامر Base2',
    collapsePanel: 'طي لوحة أوامر Base2',
    pageSections: 'أقسام صفحة Base2',
    pulseGuide: 'دليل النبض',
    pulseEnabled: 'دليل النبض مفعّل',
    navButtons: 'أزرار التنقل',
    toggleMovement: 'تبديل أزرار تنقل Base2',
    commandPalette: 'لوحة الأوامر',
    paletteLabel: 'لوحة أوامر Base2',
    closePalette: 'إغلاق لوحة أوامر Base2',
    searchActions: 'البحث في إجراءات Base2',
    colorSchemes: 'أنظمة ألوان Base2',
    useScheme: 'استخدام',
    schemeSuffix: 'كنظام ألوان',
    active: 'نشط',
    apply: 'تطبيق',
    unavailable: 'غير متاح على الموقع العام',
    publicSafe: 'متاح للعامة',
    locked: 'مقفل',
    navigation: 'التنقل',
    utilityShortcuts: 'اختصارات Base2',
    utilityPrefix: 'اختصار Base2:',
    closeUtility: 'إغلاق قائمة اختصارات Base2',
    openUtility: 'فتح قائمة اختصارات Base2',
    scrollUp: 'التمرير إلى قسم Base2 السابق',
    scrollDown: 'التمرير إلى قسم Base2 التالي',
  },
};

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

const findSection = (item) => {
  if (typeof document === 'undefined') return null;
  return (
    document.getElementById(item.target) || document.querySelector(`[data-testid="${item.target}"]`)
  );
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

const HomeObsidianNavigation = ({ onNavigate, onUtilityAction = () => {}, locale = 'en' }) => {
  const resolvedLocale = Object.hasOwn(navigationCopy, locale) ? locale : 'en';
  const copy = navigationCopy[resolvedLocale];
  const [isLeftOpen, setIsLeftOpen] = useState(false);
  const [isRightOpen, setIsRightOpen] = useState(false);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [navButtonsEnabled, setNavButtonsEnabled] = useState(true);
  const [activeSection, setActiveSection] = useState('home');
  const [activeLeftSectionSlot, setActiveLeftSectionSlot] = useState(sectionItems.length);
  const [activeUtilitySlot, setActiveUtilitySlot] = useState(utilityItems.length + 4);
  const [colorSchemeId, setColorSchemeId] = useState('volcanic');
  const [scrollState, setScrollState] = useState(getScrollMetrics);
  const movementClickTimer = useRef(null);
  const lastMovementClick = useRef({ direction: 0, time: 0 });
  const leftToggleRef = useRef(null);
  const leftMenuRef = useRef(null);
  const leftSectionListRef = useRef(null);
  const leftSectionButtonRefs = useRef([]);
  const leftSectionSnapTimer = useRef(null);
  const activeLeftSectionSlotRef = useRef(sectionItems.length);
  const activeSectionRef = useRef('home');
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
  const normalizeSectionSlot = useCallback(
    (index) => {
      const length = sectionItems.length;
      return sectionLoopOffset + (((index % length) + length) % length);
    },
    [sectionLoopOffset]
  );

  const centerLeftSectionSlot = useCallback((index, smooth = true) => {
    const scrollEl = leftSectionListRef.current;
    const target = leftSectionButtonRefs.current[index];
    if (!scrollEl || !target) return;
    const targetTop = target.offsetTop - scrollEl.clientHeight / 2 + target.offsetHeight / 2;
    if (typeof scrollEl.scrollTo === 'function') {
      scrollEl.scrollTo({ top: targetTop, behavior: smooth ? 'smooth' : 'auto' });
    } else {
      scrollEl.scrollTop = targetTop;
    }
  }, []);

  const updateActiveLeftSectionFromScroll = useCallback(
    (snap = false) => {
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
      let selectedIndex = closestIndex;
      if (snap) {
        const canonicalIndex = normalizeSectionSlot(closestIndex);
        const currentEl = buttons[closestIndex];
        const canonicalEl = leftSectionButtonRefs.current[canonicalIndex];
        if (canonicalIndex !== closestIndex && currentEl && canonicalEl) {
          scrollEl.scrollTop += canonicalEl.offsetTop - currentEl.offsetTop;
          selectedIndex = canonicalIndex;
        }
      }
      activeLeftSectionSlotRef.current = selectedIndex;
      setActiveLeftSectionSlot(selectedIndex);
      if (item && item.id !== activeSection) {
        activeSectionRef.current = item.id;
        setActiveSection(item.id);
      }
      if (snap) {
        centerLeftSectionSlot(selectedIndex, true);
      }
    },
    [activeSection, centerLeftSectionSlot, normalizeSectionSlot, visibleSectionItems]
  );

  const moveLeftSectionSlot = useCallback(
    (index, smooth = false) => {
      const nextSlot = normalizeSectionSlot(index);
      const nextItem = visibleSectionItems[nextSlot];
      if (nextItem) {
        activeLeftSectionSlotRef.current = nextSlot;
        activeSectionRef.current = nextItem.id;
        setActiveSection(nextItem.id);
        setActiveLeftSectionSlot(nextSlot);
      }
      centerLeftSectionSlot(nextSlot, smooth);
      window.clearTimeout(leftSectionSnapTimer.current);
    },
    [centerLeftSectionSlot, normalizeSectionSlot, visibleSectionItems]
  );

  const getLeftSectionDistance = useCallback(
    (index) => {
      const length = sectionItems.length;
      const activeBaseIndex =
        (((activeLeftSectionSlot - sectionLoopOffset) % length) + length) % length;
      const itemBaseIndex = (((index - sectionLoopOffset) % length) + length) % length;
      const forward = (itemBaseIndex - activeBaseIndex + length) % length;
      const signedDistance = forward > length / 2 ? forward - length : forward;
      return Math.max(-2, Math.min(2, signedDistance));
    },
    [activeLeftSectionSlot, sectionLoopOffset]
  );

  const handleLeftSectionScroll = useCallback(() => {
    updateActiveLeftSectionFromScroll(false);
    window.clearTimeout(leftSectionSnapTimer.current);
    leftSectionSnapTimer.current = window.setTimeout(
      () => updateActiveLeftSectionFromScroll(true),
      160
    );
  }, [updateActiveLeftSectionFromScroll]);

  const visibleUtilityItems = useMemo(
    () => [...utilityItems, ...utilityItems, ...utilityItems],
    []
  );
  const utilityLoopOffset = utilityItems.length;
  const normalizeUtilitySlot = useCallback(
    (index) => {
      const length = utilityItems.length;
      return utilityLoopOffset + (((index % length) + length) % length);
    },
    [utilityLoopOffset]
  );
  const activeColorScheme =
    colorSchemes.find((scheme) => scheme.id === colorSchemeId) || colorSchemes[0];

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
      activeSectionRef.current = nextActiveSection;
      setActiveSection(nextActiveSection);
    }
  }, []);

  useEffect(() => {
    activeUtilitySlotRef.current = activeUtilitySlot;
  }, [activeUtilitySlot]);

  const centerUtilitySlot = useCallback(
    (index, behavior = 'auto') => {
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
    },
    [normalizeUtilitySlot]
  );

  const updateUtilitySelectionFromScroll = useCallback(
    (shouldSettle = false) => {
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
          if (
            itemEl.getAttribute('aria-disabled') === 'true' ||
            itemEl.classList.contains('is-locked')
          )
            return;
          const itemCenter = itemEl.offsetTop + itemEl.offsetHeight / 2;
          const distance = Math.abs(itemCenter - viewportCenter);
          if (distance < nearestDistance) {
            nearestDistance = distance;
            nextSlot = index;
          }
        });

        const selectedEl = utilityItemRefs.current[nextSlot];
        if (!selectedEl) return;
        activeUtilitySlotRef.current = nextSlot;
        setActiveUtilitySlot(nextSlot);

        if (shouldSettle) {
          if (utilitySnapTimer.current) {
            window.clearTimeout(utilitySnapTimer.current);
          }
          utilitySnapTimer.current = window.setTimeout(() => {
            utilitySnapTimer.current = null;
            const canonicalSlot = normalizeUtilitySlot(nextSlot);
            const currentLoopEl = utilityItemRefs.current[nextSlot];
            const middleLoopEl = utilityItemRefs.current[canonicalSlot];
            if (canonicalSlot !== nextSlot && currentLoopEl && middleLoopEl) {
              scrollEl.scrollTop += middleLoopEl.offsetTop - currentLoopEl.offsetTop;
            }
            activeUtilitySlotRef.current = canonicalSlot;
            setActiveUtilitySlot(canonicalSlot);
            centerUtilitySlot(canonicalSlot, 'smooth');
          }, 180);
        }
      });
    },
    [centerUtilitySlot, normalizeUtilitySlot]
  );

  useEffect(() => {
    updateScrollState();
    window.addEventListener('scroll', updateScrollState, { passive: true });
    window.addEventListener('resize', updateScrollState);
    window.addEventListener('load', updateScrollState);
    window.addEventListener('pageshow', updateScrollState);

    // A responsive section can grow after the first layout pass without
    // emitting either scroll or resize (for example, when a font or deferred
    // child settles). Keep the movement controls synchronized with that final
    // document geometry instead of leaving a stale edge decision on screen.
    const resizeObserver =
      typeof ResizeObserver === 'function' ? new ResizeObserver(updateScrollState) : null;
    if (resizeObserver && document.body) resizeObserver.observe(document.body);

    const layoutFrames = [];
    layoutFrames.push(
      window.requestAnimationFrame(() => {
        layoutFrames.push(window.requestAnimationFrame(updateScrollState));
      })
    );
    return () => {
      window.removeEventListener('scroll', updateScrollState);
      window.removeEventListener('resize', updateScrollState);
      window.removeEventListener('load', updateScrollState);
      window.removeEventListener('pageshow', updateScrollState);
      resizeObserver?.disconnect();
      layoutFrames.forEach((frame) => window.cancelAnimationFrame(frame));
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
      if (leftSectionSnapTimer.current) {
        window.clearTimeout(leftSectionSnapTimer.current);
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
    menu.style.setProperty(
      'width',
      'min(var(--left-menu-width), calc(100vw - (var(--left-menu-edge) * 2)))',
      'important'
    );
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
    activeSectionRef.current = activeSection;
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
    if (isLeftOpen) return;
    window.requestAnimationFrame(() => {
      if (
        document.activeElement === document.body ||
        document.activeElement?.closest?.('[data-testid="base2-left-command-menu"]')
      ) {
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
      const nextIndex = normalizeSectionSlot(index + 1);
      moveLeftSectionSlot(nextIndex, true);
      buttons[nextIndex]?.focus();
    }
    if (event.key === 'ArrowUp' || event.key === 'ArrowLeft') {
      event.preventDefault();
      const nextIndex = normalizeSectionSlot(index - 1);
      moveLeftSectionSlot(nextIndex, true);
      buttons[nextIndex]?.focus();
    }
    if (event.key === 'Home') {
      event.preventDefault();
      const nextIndex = normalizeSectionSlot(0);
      moveLeftSectionSlot(nextIndex, true);
      buttons[nextIndex]?.focus();
    }
    if (event.key === 'End') {
      event.preventDefault();
      const nextIndex = normalizeSectionSlot(sectionItems.length - 1);
      moveLeftSectionSlot(nextIndex, true);
      buttons[nextIndex]?.focus();
    }
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      const item = visibleSectionItems[index];
      if (index === activeLeftSectionSlot && item) {
        goToSection(item.id);
      } else {
        moveLeftSectionSlot(index, true);
      }
    }
  };

  const forceSectionIntoView = useCallback(
    (item) => {
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
        const scrollHeight = Math.max(
          root.scrollHeight,
          body?.scrollHeight || 0,
          scrollRoot?.scrollHeight || 0
        );
        const maxScroll = Math.max(0, scrollHeight - window.innerHeight);
        const currentScroll =
          window.scrollY || scrollRoot?.scrollTop || root.scrollTop || body.scrollTop || 0;
        const sectionTop = section.getBoundingClientRect().top + currentScroll;
        const targetTop = Math.min(Math.max(0, sectionTop), maxScroll);
        window.scrollTo({ top: targetTop, behavior: 'auto' });
        [scrollRoot, root, body].filter(Boolean).forEach((element) => {
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
          movementAlignTimers.current = movementAlignTimers.current.filter(
            (timer) => timer.id !== alignTimer
          );
        }
      }, 180);
    },
    [clearMovementAlignTimers, scheduleMovementInterval, scheduleMovementTimeout]
  );

  const goToSection = useCallback(
    (id) => {
      const item = sectionItems.find((candidate) => candidate.id === id) || sectionItems[0];
      movementScrollLockUntilRef.current = Date.now() + 7600;
      activeSectionRef.current = item.id;
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
    const currentIndex = Math.max(
      0,
      sectionItems.findIndex((item) => item.id === activeSectionRef.current)
    );
    const targetIndex = Math.min(
      sectionItems.length - 1,
      Math.max(0, currentIndex + (direction > 0 ? 1 : -1))
    );
    goToSection(sectionItems[targetIndex].id);
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
        movementAlignTimers.current = movementAlignTimers.current.filter(
          (timer) => timer.id !== edgeTimer
        );
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
    activeSectionRef.current = target.id;
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
    if (!item.safe) return;
    const normalizedIndex = normalizeUtilitySlot(index);
    const selectedEl = utilityItemRefs.current[normalizedIndex];
    const scrollEl = utilityScrollRef.current;
    activeUtilitySlotRef.current = normalizedIndex;
    setActiveUtilitySlot(normalizedIndex);

    if (selectedEl && scrollEl) {
      // A direct selection must be atomic. Smooth scrolling can emit
      // intermediate scroll events that temporarily select another loop copy,
      // so center the canonical option before allowing scroll reconciliation.
      centerUtilitySlot(normalizedIndex, 'auto');
    }

    onUtilityAction(item.action);
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
      lang={resolvedLocale}
      dir={resolvedLocale === 'ar' ? 'rtl' : 'ltr'}
    >
      {isLeftOpen ? (
        <button
          type="button"
          className="home-left-command-backdrop"
          aria-label={copy.dismissOverlay}
          onClick={() => setIsLeftOpen(false)}
          data-testid="base2-left-menu-backdrop"
        />
      ) : null}

      <button
        type="button"
        className={`home-left-menu-toggle ${isLeftOpen ? 'is-open' : ''}`}
        ref={leftToggleRef}
        onClick={() => setIsLeftOpen((open) => !open)}
        aria-label={isLeftOpen ? copy.closeCommand : copy.openCommandMenu}
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
        style={
          isLeftOpen
            ? {
                top: 'var(--left-menu-top)',
                left: 'var(--left-menu-edge)',
                width: 'min(var(--left-menu-width), calc(100vw - (var(--left-menu-edge) * 2)))',
                height: 'min(90dvh, var(--left-menu-safe-height))',
                maxHeight: 'min(90dvh, var(--left-menu-safe-height))',
                transform: 'translate3d(0, 0, 0)',
              }
            : undefined
        }
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
            <strong>{copy.command}</strong>
          </div>
          <button
            type="button"
            className="home-left-command-close"
            onClick={() => setIsLeftOpen(false)}
            aria-label={copy.collapsePanel}
            tabIndex={isLeftOpen ? 0 : -1}
            data-testid="base2-left-menu-close"
          >
            <ChevronLeft aria-hidden="true" />
          </button>
        </div>
        <nav
          aria-label={copy.pageSections}
          className="home-left-command-list"
          ref={leftSectionListRef}
          data-testid="base2-left-section-list"
          onScroll={handleLeftSectionScroll}
        >
          {visibleSectionItems.map((item, index) => {
            const Icon = item.icon;
            const isCanonicalLoop =
              index >= sectionLoopOffset && index < sectionLoopOffset + sectionItems.length;
            const loopPosition =
              index < sectionLoopOffset ? 'previous' : isCanonicalLoop ? 'middle' : 'next';
            const isLoopBoundary = index % sectionItems.length === 0;
            const isActive = index === activeLeftSectionSlot;
            const wheelDistance = getLeftSectionDistance(index);
            return (
              <button
                type="button"
                key={`${item.id}-${index}`}
                ref={(node) => {
                  leftSectionButtonRefs.current[index] = node;
                }}
                onClick={() => (isActive ? goToSection(item.id) : moveLeftSectionSlot(index, true))}
                onKeyDown={(event) => handleLeftSectionKeyDown(event, index)}
                className={isActive ? 'is-active' : ''}
                aria-current={isActive ? 'location' : undefined}
                tabIndex={isLeftOpen ? 0 : -1}
                data-section-loop={loopPosition}
                data-wheel-distance={wheelDistance}
                data-loop-boundary={isLoopBoundary ? 'start' : undefined}
                data-testid={`base2-section-nav-${item.id}`}
              >
                <Icon aria-hidden="true" />
                <span>{copy[item.labelKey]}</span>
              </button>
            );
          })}
        </nav>
        <div className="home-left-command-switches">
          <label>
            <span>
              <Activity aria-hidden="true" /> {copy.pulseGuide}
            </span>
            <input
              type="checkbox"
              checked
              readOnly
              aria-label={copy.pulseEnabled}
              tabIndex={isLeftOpen ? 0 : -1}
            />
          </label>
          <label>
            <span>
              <LockKeyhole aria-hidden="true" /> {copy.navButtons}
            </span>
            <input
              type="checkbox"
              checked={navButtonsEnabled}
              onChange={() => setNavButtonsEnabled((enabled) => !enabled)}
              aria-label={copy.toggleMovement}
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
          <span>{copy.commandPalette}</span>
          <kbd>Ctrl K</kbd>
        </button>
      </div>

      {isCommandPaletteOpen ? (
        <div
          className="home-command-palette-modal"
          role="dialog"
          aria-modal="true"
          aria-label={copy.paletteLabel}
          data-testid="base2-command-palette"
        >
          <button
            type="button"
            className="home-command-palette-backdrop"
            aria-label={copy.closePalette}
            onClick={() => setIsCommandPaletteOpen(false)}
          />
          <div className="home-command-palette-surface">
            <div className="home-command-search-row">
              <Search aria-hidden="true" />
              <span>{copy.searchActions}</span>
              <kbd>Esc</kbd>
            </div>
            <div className="home-command-palette-actions" role="menu">
              <div
                className="home-command-palette-schemes"
                role="group"
                aria-label={copy.colorSchemes}
              >
                {colorSchemes.map((scheme) => (
                  <button
                    type="button"
                    key={scheme.id}
                    className={scheme.id === colorSchemeId ? 'is-active' : ''}
                    onClick={() => setColorSchemeId(scheme.id)}
                    aria-pressed={scheme.id === colorSchemeId}
                    aria-label={`${copy.useScheme} ${scheme.label} ${copy.schemeSuffix}`}
                    data-testid={`base2-color-scheme-${scheme.id}`}
                    style={{
                      '--scheme-primary': scheme.primary,
                      '--scheme-accent': scheme.accent,
                    }}
                  >
                    <span>{scheme.label}</span>
                    <em>{scheme.id === colorSchemeId ? copy.active : copy.apply}</em>
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
                  aria-label={`${copy[action.labelKey]}${action.safe ? '' : ` ${copy.unavailable}`}`}
                >
                  <span>{copy[action.labelKey]}</span>
                  <em>{action.safe ? copy.publicSafe : copy.locked}</em>
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
              <span>{copy.navigation}</span>
              <button
                type="button"
                onClick={() => setNavButtonsEnabled((enabled) => !enabled)}
                aria-label={copy.toggleMovement}
                aria-pressed={navButtonsEnabled}
              >
                <span className={navButtonsEnabled ? 'is-on' : ''} />
              </button>
            </div>
            <div
              className="home-right-utility-scroll"
              role="navigation"
              aria-label={copy.utilityShortcuts}
              ref={utilityScrollRef}
              data-testid="base2-right-utility-scroll"
            >
              {visibleUtilityItems.map((item, index) => {
                const Icon = item.icon;
                const isSelected = index === activeUtilitySlot;
                const isCanonicalCopy = index >= utilityLoopOffset && index < utilityLoopOffset * 2;
                return (
                  <button
                    type="button"
                    className={`home-right-utility-icon ${isSelected ? 'is-active' : ''} ${item.safe ? '' : 'is-locked'}`}
                    aria-label={`${copy.utilityPrefix} ${copy[item.labelKey]}${item.safe ? '' : ` ${copy.unavailable}`}`}
                    disabled={!item.safe}
                    aria-hidden={!isCanonicalCopy}
                    tabIndex={isCanonicalCopy ? 0 : -1}
                    ref={(node) => {
                      utilityItemRefs.current[index] = node;
                    }}
                    key={`${item.labelKey}-${index}`}
                    onClick={() => handleUtilitySelect(index, item)}
                    title={`${copy[item.labelKey]}${item.safe ? '' : ` ${copy.locked}`}`}
                  >
                    <Icon aria-hidden="true" />
                    <span>{copy[item.labelKey]}</span>
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
          aria-label={isRightOpen ? copy.closeUtility : copy.openUtility}
          aria-expanded={isRightOpen}
          data-testid="base2-right-utility-toggle"
        >
          <ChevronLeft aria-hidden="true" />
        </button>
      </div>

      {navButtonsEnabled ? (
        <div
          className="home-bottom-movement-controls"
          data-testid="base2-bottom-movement-controls"
          data-active-section={activeSection}
        >
          <output className="home-active-section-output" data-testid="base2-section-active">
            {activeSection}
          </output>
          {canMoveUp ? (
            <button
              type="button"
              className="home-movement-button home-movement-button-up"
              onClick={() => handleMovementClick(-1)}
              onDoubleClick={(event) => handleMovementDoubleClick(-1, event)}
              aria-label={copy.scrollUp}
              data-testid="base2-scroll-ascend"
            >
              <span
                className="home-movement-progress"
                style={{ height: `${scrollState.progress}%` }}
              />
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
              aria-label={copy.scrollDown}
              data-testid="base2-scroll-descend"
            >
              <span
                className="home-movement-progress"
                style={{ height: `${scrollState.progress}%` }}
              />
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
