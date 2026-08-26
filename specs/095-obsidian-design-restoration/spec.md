# Feature 095: Obsidian Design Restoration

## Objective

Restore the complete reviewed volcanic/Obsidian public experience from historical source commit `0132131292d584172a9b2fa173e439b540abed99` as a compatibility layer on top of current `main` commit `21e6fd3fdc035c3980d35dd88b10f192d675fe59`.

## Non-negotiable boundaries

- Preserve every current platform, profile, security, authentication, deployment, operator-route, CSRF, proxy, and resource fix.
- Do not merge or reset to the historical branch.
- Treat the historical branch as design evidence only and port compatible presentation and interaction behavior into the current architecture.
- Preserve staging-only ACME behavior for previews.
- Require unit, accessibility, interaction, responsive visual, build, deployment, authenticated application, and teardown validation before closeout.
- Do not expose secrets or weaken private-route controls.

## Source evidence

- Current platform baseline: `21e6fd3fdc035c3980d35dd88b10f192d675fe59`
- Historical design source: `0132131292d584172a9b2fa173e439b540abed99`
- Historical merge base: `5320d3fac8decfb77df75c10b4633821f91cea78`

## Acceptance outcomes

1. The full historical navigation, palette, section movement, utility, responsive, and page composition intent is represented in the current public site.
2. Generated site profiles and modern routes continue to work.
3. Keyboard, reduced-motion, focus, contrast, mobile, tablet, and desktop behavior are covered.
4. Visual snapshots are reviewed against the restored implementation and fail on material regression.
5. All current production gates remain green.
6. A bounded live preview proves public design plus authenticated operator applications, then tears down automatically or by exact approved cleanup.
