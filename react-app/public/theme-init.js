(function () {
  // Visitor-only bootstrap. Account choices are applied after authentication,
  // without blocking navigation; they are never put in a shared browser cookie.
  var root = document.documentElement;
  var cookieTheme = null;
  try {
    var match = document.cookie.match(/(?:^|;\s*)theme=([^;]+)/);
    var value = match ? decodeURIComponent(match[1]) : null;
    if (value === 'dark' || value === 'light') cookieTheme = value;
  } catch (_e) {
    /* A malformed/blocked cookie must not block the fallback. */
  }
  var matches = function (query) {
    return !!(window.matchMedia && window.matchMedia(query).matches);
  };
  var theme =
    cookieTheme ||
    (root.dataset.theme === 'obsidian' || matches('(prefers-color-scheme: dark)')
      ? 'dark'
      : 'light');
  root.dataset.colorMode = theme;
  root.dataset.contrast = matches('(prefers-contrast: more)') ? 'high' : 'standard';
  root.dataset.motion = matches('(prefers-reduced-motion: reduce)') ? 'reduced' : 'full';
  root.dataset.density = 'comfortable';
  if (theme === 'dark') root.classList.add('dark');
  else root.classList.remove('dark');
})();
