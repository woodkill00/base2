import { createAuthSession } from '../lib/authSession';

describe('memory-only auth session', () => {
  let data;
  let session;
  const payload = {
    email: 'synthetic@example.test',
    access_token: 'synthetic-access',
    refresh_token: 'synthetic-refresh',
    challenge_token: 'synthetic-challenge',
  };
  beforeEach(() => {
    data = new Map();
    session = createAuthSession(() => ({
      getItem: (key) => data.get(key),
      setItem: (key, value) => data.set(key, value),
      removeItem: (key) => data.delete(key),
    }));
  });
  test('purges but never imports legacy credentials and forged profile', () => {
    for (const key of ['token', 'refresh_token', 'user']) data.set(key, 'untrusted');
    data.set('unrelated-preference', 'keep');
    session.initialize();
    expect(session.access()).toBeNull();
    expect([...data]).toEqual([['unrelated-preference', 'keep']]);
  });
  test('accepts only the public profile and keeps credentials out of storage', () => {
    expect(session.accept(payload, session.epoch(), { explicit: true })).toEqual({
      email: payload.email,
    });
    expect(session.access()).toBe(payload.access_token);
    expect([...data.keys()]).toEqual(['base2.auth.version']);
    expect(session.profile(payload)).toEqual({ email: payload.email });
  });
  test('logout rejects an in-flight login or refresh response', () => {
    const epoch = session.epoch();
    session.invalidate();
    expect(session.accept(payload, epoch, { explicit: true })).toBeNull();
    expect(session.accept(payload, epoch)).toBeNull();
    expect(session.access()).toBeNull();
    expect(session.canRestore()).toBe(false);
  });
  test('explicit account replacement rejects previous-account responses', () => {
    session.accept(payload, session.epoch(), { explicit: true });
    const oldEpoch = session.epoch();
    const next = { email: 'other@example.test', access_token: 'synthetic-other' };
    expect(session.accept(next, oldEpoch, { explicit: true })).toEqual({ email: next.email });
    expect(session.epoch()).toBeGreaterThan(oldEpoch);
    expect(session.accept(payload, oldEpoch)).toBeNull();
    expect(session.access()).toBe(next.access_token);
  });
  test('logout barrier survives reload until a new explicit sign-in', () => {
    session.invalidate();
    session.initialize();
    expect(session.canRestore()).toBe(false);
    expect(session.accept(payload, session.epoch())).toBeNull();
    session.accept(payload, session.epoch(), { explicit: true });
    expect(session.canRestore()).toBe(true);
  });
  test('other-tab logout invalidates locally without rebroadcast', () => {
    const listener = vi.fn();
    const remove = session.subscribe(listener);
    session.accept(payload, session.epoch(), { explicit: true });
    session.storageChanged({ key: 'base2.auth.signed-out', newValue: '1' });
    expect(session.access()).toBeNull();
    expect(listener).toHaveBeenCalledWith('signed-out');
    expect([...data.keys()]).toEqual(['base2.auth.version']);
    remove();
    session.invalidate();
    expect(listener).toHaveBeenCalledTimes(1);
  });
  test('unrelated storage and sign-in marker removal cannot authenticate another tab', () => {
    const listener = vi.fn();
    session.subscribe(listener);
    session.storageChanged({ key: 'unrelated', newValue: 'x' });
    session.storageChanged({ key: 'base2.auth.signed-out', newValue: null });
    expect(listener).not.toHaveBeenCalled();
    expect(session.access()).toBeNull();
  });
  test('clearing storage clears private UI through subscribers', () => {
    const listener = vi.fn();
    session.subscribe(listener);
    session.storageChanged({ key: null });
    expect(listener).toHaveBeenCalledWith('signed-out');
  });

  test('a changed account version rejects refresh and clears existing tabs', () => {
    session.accept(payload, session.epoch(), { explicit: true });
    data.set('base2.auth.version', 'new-account-version');
    expect(session.canRestore()).toBe(false);
    expect(session.accept(payload, session.epoch())).toBeNull();
    session.storageChanged({ key: 'base2.auth.version', newValue: 'new-account-version' });
    expect(session.access()).toBeNull();
  });
  test('denied storage fails closed for restoration but permits explicit memory login', () => {
    session = createAuthSession(() => {
      throw new Error('denied');
    });
    session.initialize();
    expect(session.canRestore()).toBe(false);
    expect(session.accept(payload, session.epoch())).toBeNull();
    expect(session.accept(payload, session.epoch(), { explicit: true })).toEqual({
      email: payload.email,
    });
    expect(session.access()).toBe(payload.access_token);
    session.invalidate();
    expect(session.access()).toBeNull();
  });
  test.each([
    {},
    { email: payload.email },
    { access_token: 'x' },
    { email: payload.email, access_token: '' },
  ])('rejects incomplete server sessions', (invalid) => {
    expect(() => session.accept(invalid, session.epoch(), { explicit: true })).toThrow(
      'Invalid session response'
    );
    expect(session.access()).toBeNull();
  });
});
