// Return paths never preserve token-bearing queries, fragments, schemes or
// encoded separators. Keep navigation on this origin and out of auth loops.
export function authReturnPath(value, fallback = '/dashboard') {
  if (typeof value !== 'string' || value.length > 2048) return fallback;
  const path = value.split(/[?#]/, 1)[0];
  if (!/^\/(?!\/)[A-Za-z0-9/_-]*$/.test(path)) return fallback;
  if (
    path
      .split('/')
      .some((part) =>
        ['login', 'signup', 'logout', 'reset-password', 'verify-email', 'forgot-password'].includes(
          part
        )
      )
  )
    return fallback;
  return path;
}
