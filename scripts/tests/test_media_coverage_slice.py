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

    library = spec.split("test('media library", 1)[1]
    assert "expect.soft" not in library
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
    assert 'schemaVersion: 4' in spec
    assert 'unobscuredContentViewport: unobscured.toJSON()' in spec
    assert 'centerInUnobscuredContent:' in spec
    assert 'contentViewport: viewport.toJSON()' in spec
    assert 'targetIndex' in spec and 'box.bottom > viewport.top' in spec and 'box.top < viewport.bottom' in spec

    assert 'row.targets.flatMap((target) => target.overlappingControls))).toEqual([])' in spec


def test_shell_focus_margin_excludes_modal_subtrees_and_preserves_alignment_assertion():
    css = (ROOT / 'react-app/src/components/glass/volcano-layout.css').read_text()
    assert ':focus-visible:not(:where(dialog, dialog *, [role="dialog"], [role="dialog"] *, [role="alertdialog"], [role="alertdialog"] *))' in css
    native = (ROOT / 'react-app/e2e/media/media-release.spec.ts').read_text()
    assert '.toBeLessThanOrEqual(2)' in native


def test_zoom_drawer_uses_unscaled_shell_viewport_and_can_scroll_fixed_rows():
    css = (ROOT / 'react-app/src/components/glass/volcano-layout.css').read_text()
    drawer = css.split('.volcano-layout .home-obsidian-nav-layer .home-left-command-menu {')[1].split('}')[0]
    assert 'var(--volcano-viewport-height, 100dvh)' in drawer
    assert 'height: var(--left-menu-safe-height)' in drawer
    assert 'overflow-y: auto' in drawer


def test_compact_drawer_toggles_occupy_reserved_control_strip_not_content():
    css = (ROOT / 'react-app/src/components/glass/volcano-layout.css').read_text()
    assert ".volcano-layout[data-movement-layout='bottom'] .home-left-menu-toggle" in css
    assert ".volcano-layout[data-movement-layout='bottom'] .home-right-utility-menu" in css
    assert '--volcano-dock-toggle-size: clamp(44px, 2rem, 56px)' in css
    assert '--volcano-dock-toggle-top:' in css
    assert 'var(--volcano-viewport-height, 100dvh) - var(--volcano-dock-toggle-size)' in css
    assert 'width: calc(100% - 2 * (var(--volcano-dock-toggle-size) + 8px))' in css
    helper = (ROOT / 'react-app/e2e/scroll-target.ts').read_text()
    assert 'Persistent controls must not overlap visible footer content' in helper


def test_scrollport_failure_keeps_sampled_image_and_bounded_geometry_before_assertion():
    source = (ROOT / 'react-app/e2e/scroll-target.ts').read_text()
    capture = source.index('await page.screenshot({')
    geometry = source.index("'scrollport-overlap-evidence'")
    assertion = source.index("expect(footerOverlaps, 'Persistent controls")
    cleanup = source.index('await scrollPageTo(page, saved.y, saved.x)')
    assert capture < geometry < assertion < cleanup
    assert capture < source.index("await expect(page.locator('.volcano-footer-frame')).toBeInViewport()") < cleanup
    assert capture < source.index('.poll(async () => Math.abs((await pageScrollTop(page)) - max))') < cleanup
    assert source.index('if (captureFailed) throw captureFailure') > assertion
    assert 'if (!originalFailure) {' in source
    assert 'failure = cleanupError' in source
    assert source.index('if (originalFailure) throw failure') > cleanup
    assert '64 * 1024' in source


def test_detail_forced_textarea_and_lifecycle_continue_after_comparison_failure():
    css = (ROOT / 'react-app/src/styles/media-library.css').read_text()
    forced = css.split('@media (forced-colors: active) {', 1)[1]
    assert '.app-shell-root textarea,' in forced
    spec = (ROOT / 'react-app/e2e/media/media-release.spec.ts').read_text()
    detail = spec.split("test('media detail", 1)[1].split("test('media picker", 1)[0]
    assert "assertForcedSystemControl(dialog.getByLabel('Caption', { exact: true }), true)" in detail
    assert 'await expect.soft(dialog).toHaveScreenshot' in detail
    assert detail.count('expect.soft') == 1
    assert detail.index('expect.soft(dialog)') < detail.index('releaseLifecycle();')
    assert detail.index('current-media-detail-completed.png') < detail.index('Prepare restore')
    assert detail.index("toContainText('ready completed.')") < detail.index('current-media-detail-restored.png')
    assert "maxDiffPixelRatio: 0.01" in detail
