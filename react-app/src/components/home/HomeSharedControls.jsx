import { useEffect, useRef } from 'react';
import HomeObsidianNavigation from './HomeObsidianNavigation';

function Controls(state) {
  const {
    copy,
    sectionItems,
    utilityItems,
    commandActions,
    colorSchemes,
    colorSchemeId,
    setColorSchemeId,
    activeColorScheme,
    activeSection,
    goToSection,
    navButtonsEnabled,
    setNavButtonsEnabled,
    isCommandPaletteOpen,
    setIsCommandPaletteOpen,
    canMoveUp,
    canMoveDown,
    moveSection,
    onUtilityAction,
  } = state;
  const palette = useRef(null);
  useEffect(() => {
    if (isCommandPaletteOpen) {
      palette.current?.scrollIntoView({ block: 'nearest' });
      palette.current?.focus({ preventScroll: true });
    }
  }, [isCommandPaletteOpen]);
  return (
    <div
      className="shared-home-controls"
      data-active-palette={colorSchemeId}
      style={{ '--home-control-accent': activeColorScheme.accent }}
    >
      <nav aria-label={copy.pageSections}>
        {sectionItems.map(({ id, labelKey, icon: Icon }) => (
          <button
            key={id}
            data-close-rail
            aria-current={activeSection === id ? 'location' : undefined}
            onClick={() => goToSection(id)}
          >
            <Icon aria-hidden="true" />
            <span>{copy[labelKey]}</span>
          </button>
        ))}
      </nav>
      <label className="shared-home-toggle">
        <input
          type="checkbox"
          checked={navButtonsEnabled}
          aria-label={copy.toggleMovement}
          onChange={() => setNavButtonsEnabled((value) => !value)}
        />
        {copy.navButtons}
      </label>
      {navButtonsEnabled && (
        <div data-testid="shared-home-movement">
          <button
            data-close-rail
            disabled={!canMoveUp}
            onClick={() => moveSection(-1)}
            onDoubleClick={() => window.scrollTo({ top: 0, behavior: 'auto' })}
          >
            {copy.scrollUp}
          </button>
          <button
            data-close-rail
            disabled={!canMoveDown}
            onClick={() => moveSection(1)}
            onDoubleClick={() =>
              window.scrollTo({ top: document.documentElement.scrollHeight, behavior: 'auto' })
            }
          >
            {copy.scrollDown}
          </button>
        </div>
      )}
      <button
        aria-expanded={isCommandPaletteOpen}
        aria-controls="shared-home-palette"
        onClick={() => setIsCommandPaletteOpen((value) => !value)}
      >
        {copy.commandPalette} · Ctrl K
      </button>
      {isCommandPaletteOpen && (
        <section
          id="shared-home-palette"
          ref={palette}
          tabIndex={-1}
          role="region"
          aria-label={copy.paletteLabel}
        >
          <h3>{copy.colorSchemes}</h3>
          {colorSchemes.map((scheme) => (
            <button
              key={scheme.id}
              aria-pressed={scheme.id === colorSchemeId}
              data-testid={`base2-color-scheme-${scheme.id}`}
              onClick={() => setColorSchemeId(scheme.id)}
            >
              {scheme.label}
            </button>
          ))}
          {commandActions.map((action) => (
            <button
              key={action.id}
              data-close-rail
              disabled={!action.safe}
              onClick={() => action.safe && goToSection(action.sectionId)}
            >
              {copy[action.labelKey]}
            </button>
          ))}
        </section>
      )}
      <details>
        <summary>{copy.utilityShortcuts}</summary>
        {utilityItems.map(({ labelKey, icon: Icon, safe, action }) => (
          <button key={labelKey} disabled={!safe} onClick={() => safe && onUtilityAction(action)}>
            <Icon aria-hidden="true" />
            <span>
              {copy[labelKey]}
              {!safe ? ` · ${copy.locked}` : ''}
            </span>
          </button>
        ))}
      </details>
    </div>
  );
}

export default function HomeSharedControls(props) {
  return <HomeObsidianNavigation {...props} renderControls={(state) => <Controls {...state} />} />;
}
