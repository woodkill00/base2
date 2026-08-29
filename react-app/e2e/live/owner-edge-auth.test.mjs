import assert from 'node:assert/strict';
import test from 'node:test';
import { installOwnerEdgeAuth } from './owner-edge-auth.mjs';

const fixture = () => {
  let handler;
  const context = {
    async route(pattern, callback) {
      assert.equal(pattern, '**/*');
      handler = callback;
    },
  };
  const invoke = async (url, headers = { Accept: 'text/html' }) => {
    const continuations = [];
    await handler({
      request: () => ({ url: () => url, headers: () => headers }),
      continue: async (options) => continuations.push(options),
    });
    return continuations;
  };
  return { context, invoke };
};

test('sends owner authorization preemptively to one exact protected origin', async () => {
  const { context, invoke } = fixture();
  await installOwnerEdgeAuth(context, {
    domain: 'woodkilldev.com', username: 'owner', password: 'test-only-password', hosts: ['admin'],
  });
  const [continued] = await invoke('https://admin.woodkilldev.com/admin/');
  assert.match(continued.headers.Authorization, /^Basic /);
  assert.equal(continued.headers.Accept, 'text/html');
});

test('never sends authorization to sibling, deceptive, insecure, or foreign origins', async () => {
  const { context, invoke } = fixture();
  await installOwnerEdgeAuth(context, {
    domain: 'woodkilldev.com', username: 'owner', password: 'test-only-password', hosts: ['admin'],
  });
  for (const url of [
    'https://swagger.woodkilldev.com/docs',
    'https://admin.woodkilldev.com.evil.invalid/',
    'http://admin.woodkilldev.com/admin/',
    'https://example.invalid/',
  ]) {
    const [continued] = await invoke(url);
    assert.equal(continued, undefined);
  }
});

test('allows only the five fixed operator host labels', async () => {
  const { context } = fixture();
  await assert.rejects(
    installOwnerEdgeAuth(context, {
      domain: 'woodkilldev.com', username: 'owner', password: 'test-only-password', hosts: ['evil'],
    }),
    /not allowlisted/
  );
});

test('rejects missing, malformed, and control-bearing credentials', async () => {
  for (const values of [
    { domain: 'not-a-domain', username: 'owner', password: 'test-only-password', hosts: ['admin'] },
    { domain: 'woodkilldev.com', username: '', password: 'test-only-password', hosts: ['admin'] },
    { domain: 'woodkilldev.com', username: 'owner', password: 'bad\nvalue', hosts: ['admin'] },
  ]) {
    const { context } = fixture();
    await assert.rejects(installOwnerEdgeAuth(context, values));
  }
});

