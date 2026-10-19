import { authReturnPath } from '../lib/authReturnPath';

test.each([
  'https://evil.test',
  '//evil.test',
  '/\\evil.test',
  '/%2f%2fevil.test',
  '/login',
  '/reset-password',
  '/a/../login',
  null,
  '',
])('rejects unsafe return path %s', (value) => {
  expect(authReturnPath(value)).toBe('/dashboard');
});
test.each(['/settings/profile', '/dashboard', '/'])(
  'retains safe path %s without credential queries',
  (path) => {
    expect(authReturnPath(`${path}?token=synthetic#secret`)).toBe(path);
  }
);
