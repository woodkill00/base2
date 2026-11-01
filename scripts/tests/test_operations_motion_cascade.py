"""Specificity regression for the native exact-zero reduced-motion failure."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def specificity(selector):
    # These application rules use only type, class, attribute and pseudo-element
    # selectors. Fail closed if a future compound selector needs a richer parser.
    assert not re.search(r"(?<!:):(?!:)|[>+~#]", selector)
    attributes = re.findall(r"\[[^]]+\]", selector)
    plain = re.sub(r"\[[^]]+\]", "", selector)
    classes = re.findall(r"\.[\w-]+", plain)
    elements = re.findall(r"::[\w-]+", plain)
    plain = re.sub(r"\.[\w-]+|::[\w-]+", "", plain)
    return (0, len(attributes) + len(classes), len(elements) + len(re.findall(r"[a-zA-Z][\w-]*", plain)))


def test_operations_exact_zero_beats_global_preference_rule():
    appearance = (ROOT / "react-app/src/styles/appearance.css").read_text()
    page = (ROOT / "react-app/src/pages/OperationsCenter.jsx").read_text()
    global_rule = re.search(r"(html\[data-motion='reduced'\][^{]+)\{([^}]+)\}", appearance)
    local_rule = re.search(r"@media \(prefers-reduced-motion: reduce\)\s*\{\s*([^{}]+)\{([^}]+)\}", page)
    assert global_rule and local_rule
    assert "transition-duration: 0.01ms !important" in global_rule[2]
    assert "transition-duration: 0s !important" in local_rule[2]
    assert "animation-duration: 0s !important" in local_rule[2]
    global_selectors = global_rule[1].strip().split(",")
    local_selectors = local_rule[1].strip().split(",")
    for suffix in ("*", "*::before", "*::after"):
        preference = next(s.strip() for s in global_selectors if s.strip().endswith(" " + suffix))
        scoped = next(s.strip() for s in local_selectors if s.strip().endswith(" " + suffix))
        assert ".operations-center " in scoped
        assert specificity(scoped) > specificity(preference), (scoped, preference)
    # The fix must stay inside the OS reduced-motion condition. Normal mode
    # remains governed by the existing design rules.
    assert page.count("transition-duration: 0s !important") == 1
    native = (ROOT / "react-app/e2e/operations/operations-release.spec.ts").read_text()
    assert "expect(transitionDuration).toBe('0s')" in native


def test_available_width_grids_preserve_readable_rem_minimums():
    page = (ROOT / 'react-app/src/pages/OperationsCenter.jsx').read_text()
    assert 'sm:grid-cols-3' not in page and 'lg:grid-cols-3' not in page
    assert 'repeat(auto-fit, minmax(min(100%, var(--operations-card-min, 18rem)), 1fr))' in page
    assert '.operations-readable-grid > *' in page
    assert 'overflow-wrap: break-word' in page
    assert 'operations-summary-grid' in page


def test_comparison_errors_are_soft_only_at_comparison_and_remain_native_failures():
    native = (ROOT / 'react-app/e2e/operations/operations-release.spec.ts').read_text()
    assert 'await expect.soft(page).toHaveScreenshot(name, { ...options, maxDiffPixelRatio });' in native
    assert 'const previousErrors = testInfo.errors.length' in native
    assert 'if (testInfo.errors.length === previousErrors)' in native
    assert "await captureScrollportExtent(page, testInfo, name.replace(/\\.png$/, ''))" in native
    assert 'expect.soft' not in native.replace('expect.soft(page).toHaveScreenshot', '')


def test_workspace_record_split_uses_available_width_and_does_not_clip():
    source = (ROOT / 'react-app/src/pages/ContentWorkspace.jsx').read_text()
    assert 'xl:grid-cols-[minmax(15rem,0.8fr)_minmax(18rem,1.2fr)]' not in source
    assert 'repeat(auto-fit, minmax(min(100%, 18rem), 1fr))' in source
    assert '.workspace-records-grid > * { min-inline-size: 0; }' in source
    native = (ROOT / 'react-app/e2e/workspace/workspace-release.spec.ts').read_text()
    assert 'Record details must remain enclosed' in native
