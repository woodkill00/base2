import { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  ArrowDown,
  ArrowUp,
  Bell,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
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

const leftItems = [
  { id: 'home', label: 'Home', icon: LayoutGrid },
  { id: 'features', label: 'Features', icon: Zap },
  { id: 'base2-obsidian-ops', label: 'Command', icon: Search },
  { id: 'base2-thermal-security', label: 'Security', icon: ShieldCheck },
  { id: 'contact', label: 'Contact', icon: Server },
];

const utilityItems = [Settings, Bell, Share2, History, Shield, Zap, Search, User, Heart, LogOut];

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

const HomeObsidianNavigation = ({ onNavigate }) => {
  const [isLeftOpen, setIsLeftOpen] = useState(false);
  const [isRightOpen, setIsRightOpen] = useState(true);
  const [navButtonsEnabled, setNavButtonsEnabled] = useState(true);
  const [scrollState, setScrollState] = useState(getScrollMetrics);

  const visibleUtilityItems = useMemo(
    () => [...utilityItems, ...utilityItems, ...utilityItems],
    []
  );

  useEffect(() => {
    const update = () => setScrollState(getScrollMetrics());
    update();
    window.addEventListener('scroll', update, { passive: true });
    window.addEventListener('resize', update);
    return () => {
      window.removeEventListener('scroll', update);
      window.removeEventListener('resize', update);
    };
  }, []);

  const handleLeftNav = (id) => {
    setIsLeftOpen(false);
    if (id === 'home' || id === 'features') {
      onNavigate(id);
      return;
    }

    const section = document.querySelector(`[data-testid="${id}"]`) || document.getElementById(id);
    if (section) {
      section.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  const scrollByPage = (direction) => {
    window.scrollBy({ top: window.innerHeight * 0.86 * direction, behavior: 'smooth' });
  };

  const scrollToEdge = (top) => {
    window.scrollTo({ top: top ? 0 : document.documentElement.scrollHeight, behavior: 'smooth' });
  };

  return (
    <div className="home-obsidian-nav-layer" data-testid="base2-obsidian-navigation">
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
          <span>Base2</span>
          <strong>Command</strong>
        </div>
        <nav aria-label="Base2 page sections" className="home-left-command-list">
          {leftItems.map((item) => {
            const Icon = item.icon;
            return (
              <button type="button" key={item.id} onClick={() => handleLeftNav(item.id)}>
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
            <input type="checkbox" checked readOnly aria-label="Pulse guide enabled" />
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
            />
          </label>
        </div>
      </div>

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
            <div className="home-right-utility-scroll" role="listbox" aria-label="Base2 utility shortcuts">
              {visibleUtilityItems.map((Icon, index) => (
                <div className="home-right-utility-icon" role="option" aria-selected={index === 10} key={index}>
                  <Icon aria-hidden="true" />
                </div>
              ))}
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
        <div className="home-bottom-movement-controls" data-testid="base2-bottom-movement-controls">
          {scrollState.canAscend ? (
            <button
              type="button"
              className="home-movement-button home-movement-button-up"
              onClick={() => scrollByPage(-1)}
              onDoubleClick={() => scrollToEdge(true)}
              aria-label="Scroll up"
              data-testid="base2-scroll-ascend"
            >
              <span className="home-movement-progress" style={{ height: `${scrollState.progress}%` }} />
              <ChevronUp aria-hidden="true" />
              <ArrowUp aria-hidden="true" />
            </button>
          ) : null}

          {scrollState.canDescend ? (
            <button
              type="button"
              className="home-movement-button home-movement-button-down"
              onClick={() => scrollByPage(1)}
              onDoubleClick={() => scrollToEdge(false)}
              aria-label="Scroll down"
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
