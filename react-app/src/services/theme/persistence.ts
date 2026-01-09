export function setThemeCookie(theme: 'light' | 'dark', days = 180) {
  const expires = new Date(Date.now() + days * 24 * 60 * 60 * 1000).toUTCString();
  const parts = [
    `theme=${encodeURIComponent(theme)}`,
    `Expires=${expires}`,
    'Path=/',
    'Secure',
    'SameSite=Lax',
    'Domain=.woodkilldev.com',
  ];
  document.cookie = parts.join('; ');
}

export function getThemeCookie(): 'light' | 'dark' | null {
  const m = document.cookie.match(/(?:^|; )theme=([^;]+)/);
  if (!m) return null;
  const v = decodeURIComponent(m[1]);
  return v === 'dark' || v === 'light' ? (v as 'light' | 'dark') : null;
}

export function applyThemeClass(theme: 'light' | 'dark') {
  const root = document.documentElement;
  if (theme === 'dark') root.classList.add('dark');
  else root.classList.remove('dark');
}
