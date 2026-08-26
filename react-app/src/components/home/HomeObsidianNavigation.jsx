import { useEffect, useMemo, useState } from 'react';
import {
  ArrowDown,
  ArrowUp,
  Bell,
  Command,
  Heart,
  History,
  LayoutGrid,
  LockKeyhole,
  Search,
  Server,
  Settings,
  Share2,
  Shield,
  ShieldCheck,
  User,
  Zap,
} from 'lucide-react';

const sections = [
  { id: 'home', label: 'Home', target: 'home-page', icon: LayoutGrid },
  { id: 'features', label: 'Features', target: 'features', icon: Zap },
  { id: 'command', label: 'Command', target: 'base2-obsidian-ops', icon: Command },
  { id: 'security', label: 'Security', target: 'base2-thermal-security', icon: ShieldCheck },
  { id: 'contact', label: 'Contact', target: 'contact', icon: Server },
];
const utilities = [
  { label: 'Settings', icon: Settings },
  { label: 'Notifications', icon: Bell },
  { label: 'Share', icon: Share2 },
  { label: 'History', icon: History },
  { label: 'Security', icon: Shield },
  { label: 'Search', icon: Search },
  { label: 'Profile', icon: User },
  { label: 'Favorites', icon: Heart },
];
const palettes = {
  volcanic: ['#ff3131', '#ff6321', '#131313'],
  ember: ['#ff7a18', '#ffd166', '#17120f'],
  basalt: ['#66e3ff', '#b5f7ff', '#101518'],
};

const HomeObsidianNavigation = ({ onNavigate }) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const [utilityOpen, setUtilityOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [active, setActive] = useState('home');
  const [progress, setProgress] = useState(0);
  const [palette, setPalette] = useState('volcanic');

  useEffect(() => {
    const update = () => {
      const root = document.documentElement;
      const maximum = Math.max(1, root.scrollHeight - window.innerHeight);
      setProgress(Math.round(Math.min(100, Math.max(0, (window.scrollY / maximum) * 100))));
      let current = 'home';
      sections.forEach((section) => {
        const element = document.getElementById(section.target);
        if (element?.getBoundingClientRect().top <= Math.min(220, window.innerHeight * 0.34)) {
          current = section.id;
        }
      });
      setActive(current);
    };
    const keyboard = (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setPaletteOpen(true);
      } else if (event.key === 'Escape') {
        setMenuOpen(false);
        setUtilityOpen(false);
        setPaletteOpen(false);
      }
    };
    update();
    window.addEventListener('scroll', update, { passive: true });
    window.addEventListener('resize', update);
    window.addEventListener('keydown', keyboard);
    return () => {
      window.removeEventListener('scroll', update);
      window.removeEventListener('resize', update);
      window.removeEventListener('keydown', keyboard);
    };
  }, []);

  const filtered = useMemo(
    () => sections.filter((section) => section.label.toLowerCase().includes(query.toLowerCase())),
    [query]
  );
  const chooseSection = (section) => {
    setActive(section.id);
    setMenuOpen(false);
    setPaletteOpen(false);
    onNavigate?.(section.id);
  };
  const selectPalette = (name) => {
    const [primary, accent, surface] = palettes[name];
    setPalette(name);
    const layer = document.querySelector('.home-obsidian-nav-layer');
    layer?.style.setProperty('--obsidian-primary', primary);
    layer?.style.setProperty('--obsidian-accent', accent);
    layer?.style.setProperty('--obsidian-surface', surface);
  };
  const move = (direction) => {
    const ordered = sections
      .map((section) => ({
        ...section,
        element: document.getElementById(section.target),
      }))
      .filter((section) => section.element);
    const index = Math.max(
      0,
      ordered.findIndex((section) => section.id === active)
    );
    const next = ordered[Math.min(ordered.length - 1, Math.max(0, index + direction))];
    if (next) chooseSection(next);
  };

  return (
    <div
      className={`home-obsidian-nav-layer home-palette-${palette}`}
      data-active-palette={palette}
      data-testid="base2-obsidian-navigation"
    >
      <button
        type="button"
        className={`home-left-menu-toggle ${menuOpen ? 'is-open' : ''}`}
        aria-label={menuOpen ? 'Close command menu' : 'Open command menu'}
        aria-expanded={menuOpen}
        onClick={() => {
          setMenuOpen((value) => !value);
          setUtilityOpen(false);
        }}
      >
        <Command aria-hidden="true" />
      </button>
      {menuOpen && (
        <button
          className="home-left-command-backdrop"
          aria-label="Close command menu"
          onClick={() => setMenuOpen(false)}
        />
      )}
      <nav
        className={`home-left-command-menu ${menuOpen ? 'is-open' : ''}`}
        aria-label="Obsidian sections"
        hidden={!menuOpen}
      >
        <div className="home-left-command-title">
          <LockKeyhole aria-hidden="true" />
          <div>
            <span>Base2</span>
            <strong>Obsidian command</strong>
          </div>
        </div>
        <div className="home-left-command-list">
          {sections.map((section) => {
            const Icon = section.icon;
            return (
              <button
                key={section.id}
                type="button"
                aria-current={active === section.id ? 'page' : undefined}
                onClick={() => chooseSection(section)}
              >
                <Icon aria-hidden="true" />
                <span>{section.label}</span>
              </button>
            );
          })}
        </div>
        <fieldset className="home-left-command-switches">
          <legend>Interface palette</legend>
          {Object.keys(palettes).map((name) => (
            <label key={name}>
              <span>{name}</span>
              <input
                type="radio"
                name="obsidian-palette"
                checked={palette === name}
                onChange={() => selectPalette(name)}
              />
            </label>
          ))}
        </fieldset>
        <button type="button" onClick={() => setPaletteOpen(true)}>
          <Search aria-hidden="true" /> Open command palette
        </button>
      </nav>

      <div className={`home-right-utility-menu ${utilityOpen ? 'is-open' : ''}`}>
        <button
          type="button"
          className="home-right-utility-toggle"
          aria-label={utilityOpen ? 'Close utility rail' : 'Open utility rail'}
          aria-expanded={utilityOpen}
          onClick={() => {
            setUtilityOpen((value) => !value);
            setMenuOpen(false);
          }}
        >
          <Settings aria-hidden="true" />
        </button>
        <aside
          className="home-right-utility-panel"
          aria-label="Preview utilities"
          hidden={!utilityOpen}
        >
          <div className="home-right-utility-nav-toggle">
            <button type="button">
              <span className="is-on">Safe preview controls</span>
            </button>
          </div>
          <div className="home-right-utility-scroll">
            {utilities.map((utility) => {
              const Icon = utility.icon;
              return (
                <button
                  key={utility.label}
                  type="button"
                  className="home-right-utility-icon"
                  title={utility.label}
                >
                  <Icon aria-hidden="true" />
                  <span>{utility.label}</span>
                </button>
              );
            })}
          </div>
        </aside>
      </div>

      <nav className="home-bottom-movement-controls" aria-label="Section movement">
        <button
          type="button"
          className="home-movement-button"
          aria-label="Previous section"
          onClick={() => move(-1)}
          disabled={active === 'home'}
        >
          <ArrowUp />
        </button>
        <button
          type="button"
          className="home-movement-button"
          aria-label="Next section"
          onClick={() => move(1)}
          disabled={active === 'contact'}
        >
          <ArrowDown />
        </button>
      </nav>
      <output className="home-active-section-output" aria-live="polite">
        {active} · {progress}%
      </output>

      {paletteOpen && (
        <div
          className="home-command-palette-modal"
          role="dialog"
          aria-modal="true"
          aria-label="Command palette"
        >
          <label htmlFor="home-command-query">Find a section</label>
          <input
            id="home-command-query"
            autoFocus
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <div className="home-command-palette-list">
            {filtered.map((section) => (
              <button key={section.id} type="button" onClick={() => chooseSection(section)}>
                {section.label}
              </button>
            ))}
          </div>
          <button type="button" onClick={() => setPaletteOpen(false)}>
            Close
          </button>
        </div>
      )}
    </div>
  );
};

export default HomeObsidianNavigation;
