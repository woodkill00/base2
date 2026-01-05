export function ensureBackdropSupport() {
  try {
    const supported =
      typeof CSS !== 'undefined' && CSS.supports && CSS.supports('backdrop-filter: blur(1px)');
    const root = document.documentElement;
    if (!supported) {
      root.classList.add('no-backdrop');
    } else {
      root.classList.remove('no-backdrop');
    }
  } catch (e) {
    // If detection fails, prefer safety: enable fallback
    document.documentElement.classList.add('no-backdrop');
  }
}
