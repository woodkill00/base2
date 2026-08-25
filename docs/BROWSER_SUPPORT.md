# Browser and device support

Base2 supports the latest two stable releases of Chromium-based browsers, Firefox, and Safari, plus the corresponding current Android Chrome and iOS Safari releases. The compatibility floor is Chrome/Edge 120, Firefox 121, Safari/iOS 17.4, with JavaScript enabled. Internet Explorer and browsers without ES2022 module support are unsupported.

The required compatibility gate uses Playwright-managed engines rather than host-installed browsers. It exercises Chromium, Firefox, and WebKit on desktop plus Chromium and WebKit touch/mobile profiles. Every project uses a fixed locale, UTC timezone, reduced motion, blocked service workers, one worker, no retries, and a local-only network boundary.

The matrix verifies:

- branded shell rendering and responsive overflow;
- no external response before user action;
- keyboard focus and touch navigation;
- supported locale routing with deterministic base-content fallback;
- explicit failure behavior after a simulated offline transition.

Real assistive-technology and physical-device observations remain part of the final T069 and T111 acceptance checkpoints; automated engine emulation is not represented as a substitute for those observations.
