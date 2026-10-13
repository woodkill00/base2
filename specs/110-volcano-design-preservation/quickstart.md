# Local reference verification

From native WSL `/home/woodkill/code/base2`:

```bash
python3 -m unittest discover -s specs/110-volcano-design-preservation -p 'test_*.py'
cd react-app
LAYOUT_ATTEMPT=volcano-review-unique-id npx playwright test --config=playwright.volcano.config.mjs
```

Choose a fresh attempt ID. Do not use `--update-snapshots` to clear regressions.
The separate Volcano harness enables the isolated restoration switch. The original
Feature 109 harness still covers its unchanged consumers; neither is evidence of
owner approval. Open `review.html` beside this document for the original reference.

The owner confirmed this exact appearance on 2026-10-13. The same components now
wrap other route families in the isolated preview. Do not enable the restoration
switch in deployment until the remaining release checks and source-bound visual
reviews are complete. Preview requires both VITE_LAYOUT109_PREVIEW=true and
VITE_VOLCANO110_PREVIEW=true with VITE_SITE_PROFILE=base2-obsidian; the dedicated
Playwright configuration supplies these explicitly.
