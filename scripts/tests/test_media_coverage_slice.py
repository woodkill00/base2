import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_counter_retains_intrinsic_width_and_toolbar_can_wrap():
    css = (ROOT / "react-app/src/styles/media-library.css").read_text()
    toolbar = re.search(r"\.media-toolbar \{([^}]+)\}", css)[1]
    counter = re.search(r"\.media-selection \{([^}]+)\}", css)[1]
    assert "display: flex" in toolbar and "flex-wrap: wrap" in toolbar
    assert "white-space: nowrap" in counter
    assert "inline-size: max-content" in counter
    assert "flex: 0 0 auto" in counter
    assert ".media-toolbar > form" in css and ".media-toolbar > label" in css


def test_supplementary_evidence_does_not_replace_pending_references():
    spec = (ROOT / "react-app/e2e/media/media-release.spec.ts").read_text()
    for name in ("current-media-detail-top.png", "current-media-detail-completed.png",
                 "current-media-picker-bottom.png", "current-media-library-viewport-"):
        assert name in spec
    assert spec.index("current-media-detail-top.png") < spec.index("const lifecycleRelease")
    assert spec.index("releaseLifecycle();") < spec.index("current-media-detail-completed.png")
    assert spec.index("soft deleted completed.") < spec.index("current-media-detail-completed.png")
    assert "toHaveScreenshot(`media-detail-${testInfo.project.name}.png`" in spec
    assert "toHaveScreenshot(`media-picker-${testInfo.project.name}.png`" in spec
    assert "toHaveScreenshot(`media-library-${testInfo.project.name}.png`" in spec
    assert spec.count("toHaveScreenshot(") == 3
    assert spec.count("maxDiffPixelRatio: 0.01") == 3
    assert "document.elementFromPoint" in spec
    assert "media-viewport-observations" in spec
    assert "whiteSpace" in spec and "scrollWidth" in spec


def test_mobile_preview_constrains_intrinsic_width_without_hiding_content():
    css = (ROOT / 'react-app/src/styles/media-library.css').read_text()
    mobile = css.split('@media (max-width: 44rem) {', 1)[1].split('\n}', 1)[0]
    assert '.media-detail-layout { grid-template-columns: minmax(0, 1fr); }' in mobile
    assert '.media-safe-preview { min-inline-size: 0; inline-size: 100%; }' in mobile
    assert 'min-block-size: 14rem' in css
    spec = (ROOT / 'react-app/e2e/media/media-release.spec.ts').read_text()
    assert 'dialogOverflow' in spec and 'previewFitsInline' in spec
    assert ").toBeInViewport({ ratio: 1 });" in spec


def test_comparison_precedes_diagnostic_scrolling_and_keeps_failure():
    spec = (ROOT / 'react-app/e2e/media/media-release.spec.ts').read_text()
    comparison = spec.index('expect(page).toHaveScreenshot(`media-library-')
    current = spec.index("path: testInfo.outputPath('current-media-library.png')")
    cleanup = spec.index('await screenshotHeaderStyle.evaluate((node) => node.parentNode?.removeChild(node))')
    diagnostics = spec.index('const viewportObservations = []')
    assert comparison < current < cleanup < diagnostics
    assert "await expect(shellHeader).toHaveCSS('position', 'sticky');" in spec[cleanup:diagnostics]
    assert 'scrollIntoView' not in spec[spec.index("const shellHeader ="):comparison]

    assert "expect.soft" not in spec
    assert "if (comparisonFailure) throw comparisonFailure;" in spec


def test_preview_foreground_and_all_visible_card_diagnostics():
    css = (ROOT / 'react-app/src/styles/media-library.css').read_text()
    preview = re.search(r'\.media-safe-preview \{([^}]+)\}', css)[1]
    assert 'color: #f8fafc' in preview
    assert 'forced-color-adjust' not in preview
    spec = (ROOT / 'react-app/e2e/media/media-release.spec.ts').read_text()
    assert 'expect(Math.min(...previewContrast)).toBeGreaterThanOrEqual(4.5)' in spec
    assert 'expect(previewContrast).toHaveLength(2)' in spec
    assert 'const observation = await cards.evaluateAll' in spec
    assert 'schemaVersion: 2' in spec
    assert 'targetIndex' in spec and 'box.bottom > 0' in spec and 'box.top < innerHeight' in spec
