"""Portal scope must preserve the existing Obsidian tokens, not create a shell root."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_portal_shares_authored_card_button_and_focus_rules():
    css = (ROOT / 'react-app/src/styles/experience.css').read_text()
    scope = ":is(.app-shell-root, .base2-modal-surface)"
    for selector, declaration in [
        ('.base2-card', 'background: var(--color-surface)'),
        ('.base2-button--danger', 'color: var(--color-danger)'),
        ('.base2-button--danger', 'background: var(--color-danger-surface, var(--color-surface))'),
        (':where(input, button, select, textarea, a):focus-visible', 'outline: 2px solid var(--color-focus)'),
    ]:
        pattern = re.escape("[data-theme='obsidian'] " + scope + ' ' + selector) + r'\s*\{([^}]+)\}'
        rule = re.search(pattern, css)
        assert rule and declaration in rule[1], selector
    page = (ROOT / 'react-app/src/pages/OperationsCenter.jsx').read_text()
    portal = page[page.index('? createPortal('):]
    assert 'base2-modal-surface operations-cancel-modal' in portal
    assert 'app-shell-root' not in portal


def test_portal_exact_motion_and_system_palette_remain_scoped():
    page = (ROOT / 'react-app/src/pages/OperationsCenter.jsx').read_text()
    rule = re.search(r'@media \(prefers-reduced-motion: reduce\)\s*\{\s*([^{}]+)\{([^}]+)\}', page)
    assert rule
    for suffix in ('*', '*::before', '*::after'):
        assert 'html body .operations-cancel-modal ' + suffix in rule[1]
    assert 'transition-duration: 0s !important' in rule[2]
    assert 'animation-duration: 0s !important' in rule[2]
    css = (ROOT / 'react-app/src/styles/experience.css').read_text()
    forced = css[css.index('@media (forced-colors: active)'):]
    assert '.base2-modal-surface .base2-button' in forced
    assert 'background: ButtonFace' in forced and 'color: ButtonText' in forced
    assert 'outline-color: Highlight' in forced
    assert 'forced-color-adjust: auto' in forced
    assert 'forced-color-adjust: none' not in forced
