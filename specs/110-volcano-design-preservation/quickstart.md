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

The next step requires confirmation of this exact appearance before all-page
composition work. Do not enable the restoration switch in deployment yet.
