import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { googleNginxPolicy } from './google-nginx-policy.mjs';
const source = readFileSync(new URL('../nginx/default.conf', import.meta.url), 'utf8');
test('disabled Google leaves browser policy byte-identical', () => {
  for (const value of ['', 'disabled', undefined])
    assert.equal(googleNginxPolicy(source, value), source);
});
test('configured Google grants only fixed GIS endpoints and preserves protections', () => {
  const output = googleNginxPolicy(source, 'synthetic.apps.googleusercontent.com');
  for (const directive of [
    "default-src 'self'",
    "base-uri 'self'",
    "object-src 'none'",
    "frame-ancestors 'none'",
    "form-action 'self'",
  ]) {
    assert.ok(output.includes(directive));
  }
  assert.ok(output.includes("script-src 'self' https://accounts.google.com/gsi/client;"));
  assert.ok(output.includes("connect-src 'self' https://accounts.google.com/gsi/;"));
  assert.ok(output.includes("frame-src 'self' https://accounts.google.com/gsi/;"));
  assert.ok(
    output.includes("style-src 'self' 'unsafe-inline' https://accounts.google.com/gsi/style;")
  );
  assert.ok(!output.includes('synthetic'));
  assert.ok(!output.includes('unsafe-eval'));
});
test('invalid input and template drift fail closed', () => {
  for (const value of [
    'bad',
    'x.apps.googleusercontent.com; evil',
    'x.apps.googleusercontent.com\n',
  ]) {
    assert.throws(() => googleNginxPolicy(source, value), /Invalid Google client/);
  }
  assert.throws(
    () => googleNginxPolicy('', 'x.apps.googleusercontent.com'),
    /Unexpected browser policy/
  );
  assert.throws(
    () => googleNginxPolicy(source + source, 'x.apps.googleusercontent.com'),
    /Unexpected browser policy/
  );
});
