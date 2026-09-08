import { useCallback, useEffect, useState } from 'react';

import AppShell from '../components/glass/AppShell';
import GlassButton from '../components/glass/GlassButton';
import GlassCard from '../components/glass/GlassCard';
import GlassInput from '../components/glass/GlassInput';
import Navigation from '../components/Navigation';
import { identityAdminAPI } from '../services/identityAdmin';

const safeList = (value) => (Array.isArray(value) ? value : []);

const ACCOUNT_COPY = {
  en: {
    shell: 'Account security',
    menu: 'Menu',
    theme: 'Toggle color theme',
    footer: 'Private workspace',
    sidebar: 'Sidebar',
    sidebarItems: ['Home', 'Dashboard', 'Settings', 'Users', 'Help'],
    title: 'Account security',
    loadError:
      'Account security information is temporarily unavailable. No sensitive response details were retained.',
    revoked: 'Session revoked. The session inventory has been refreshed.',
    revokeError: 'The session could not be revoked. Try again after reauthenticating.',
    setupStarted: 'Authenticator setup started. Confirm the current six-digit code.',
    setupError: 'Authenticator setup could not start. Reauthenticate and try again.',
    enabled: 'Authenticator enabled. Save the recovery codes now; they will not be shown again.',
    codeError: 'The code was not accepted. No authenticator change was made.',
    recoveryReplaced: 'Recovery codes replaced. Save them now; they will not be shown again.',
    recoveryError: 'Recovery codes could not be replaced. Reauthenticate and verify the code.',
    mfa: 'Multi-factor authentication',
    authenticator: 'Authenticator app',
    authenticatorHelp: 'Use a time-based one-time password after reauthentication.',
    setup: 'Set up authenticator',
    enrollmentUnavailable:
      'Enrollment is unavailable until encrypted secret storage is configured.',
    recovery: 'Recovery codes',
    recoveryHelp: 'Recovery codes are shown only once. Store them outside this site.',
    recoveryCreated: 'New codes are created when authenticator enrollment is confirmed.',
    currentCode: 'Current authenticator code',
    replaceRecovery: 'Replace recovery codes',
    passkeys: 'Passkeys',
    addPasskey: 'Add a passkey',
    passkeysUnavailable: 'Passkeys are not enabled for this site.',
    confirmAuthenticator: 'Confirm authenticator',
    setupUri: 'Open this setup URI in your authenticator:',
    sixDigit: 'Six-digit code',
    confirm: 'Confirm authenticator',
    oneTimeCodes: 'One-time recovery codes',
    sessions: 'Sessions',
    refresh: 'Refresh sessions',
    noSessions: 'No sessions are available.',
    unknownDevice: 'Unknown device',
    currentSession: 'Current session',
    otherSession: 'Other session',
    revoking: 'Revoking…',
    revoke: 'Revoke',
  },
  de: {
    shell: 'Kontosicherheit',
    menu: 'Menü',
    theme: 'Farbschema wechseln',
    footer: 'Privater Arbeitsbereich',
    sidebar: 'Seitenleiste',
    sidebarItems: ['Start', 'Übersicht', 'Einstellungen', 'Benutzer', 'Hilfe'],
    title: 'Kontosicherheit',
    loadError:
      'Informationen zur Kontosicherheit sind vorübergehend nicht verfügbar. Vertrauliche Antwortdetails wurden nicht gespeichert.',
    revoked: 'Sitzung widerrufen. Die Sitzungsliste wurde aktualisiert.',
    revokeError:
      'Die Sitzung konnte nicht widerrufen werden. Melden Sie sich erneut an und versuchen Sie es noch einmal.',
    setupStarted:
      'Die Authenticator-Einrichtung wurde gestartet. Bestätigen Sie den aktuellen sechsstelligen Code.',
    setupError:
      'Die Authenticator-Einrichtung konnte nicht gestartet werden. Melden Sie sich erneut an.',
    enabled:
      'Authenticator aktiviert. Speichern Sie die Wiederherstellungscodes jetzt; sie werden nicht erneut angezeigt.',
    codeError: 'Der Code wurde nicht akzeptiert. Der Authenticator wurde nicht geändert.',
    recoveryReplaced:
      'Wiederherstellungscodes ersetzt. Speichern Sie sie jetzt; sie werden nicht erneut angezeigt.',
    recoveryError:
      'Die Wiederherstellungscodes konnten nicht ersetzt werden. Melden Sie sich erneut an und prüfen Sie den Code.',
    mfa: 'Mehrstufige Authentifizierung',
    authenticator: 'Authenticator-App',
    authenticatorHelp: 'Verwenden Sie nach erneuter Anmeldung ein zeitbasiertes Einmalkennwort.',
    setup: 'Authenticator einrichten',
    enrollmentUnavailable:
      'Die Einrichtung ist erst verfügbar, wenn verschlüsselte Geheimnisspeicherung konfiguriert ist.',
    recovery: 'Wiederherstellungscodes',
    recoveryHelp:
      'Wiederherstellungscodes werden nur einmal angezeigt. Speichern Sie sie außerhalb dieser Website.',
    recoveryCreated: 'Neue Codes werden nach Bestätigung der Authenticator-Einrichtung erstellt.',
    currentCode: 'Aktueller Authenticator-Code',
    replaceRecovery: 'Wiederherstellungscodes ersetzen',
    passkeys: 'Passkeys',
    addPasskey: 'Passkey hinzufügen',
    passkeysUnavailable: 'Passkeys sind für diese Website nicht aktiviert.',
    confirmAuthenticator: 'Authenticator bestätigen',
    setupUri: 'Öffnen Sie diese Einrichtungs-URI in Ihrem Authenticator:',
    sixDigit: 'Sechsstelliger Code',
    confirm: 'Authenticator bestätigen',
    oneTimeCodes: 'Einmalige Wiederherstellungscodes',
    sessions: 'Sitzungen',
    refresh: 'Sitzungen aktualisieren',
    noSessions: 'Keine Sitzungen verfügbar.',
    unknownDevice: 'Unbekanntes Gerät',
    currentSession: 'Aktuelle Sitzung',
    otherSession: 'Andere Sitzung',
    revoking: 'Wird widerrufen…',
    revoke: 'Widerrufen',
  },
  ar: {
    shell: 'أمان الحساب',
    menu: 'القائمة',
    theme: 'تبديل سمة الألوان',
    footer: 'مساحة عمل خاصة',
    sidebar: 'الشريط الجانبي',
    sidebarItems: ['الرئيسية', 'لوحة المعلومات', 'الإعدادات', 'المستخدمون', 'المساعدة'],
    title: 'أمان الحساب',
    loadError: 'معلومات أمان الحساب غير متاحة مؤقتًا. لم يتم الاحتفاظ بتفاصيل الاستجابة الحساسة.',
    revoked: 'تم إلغاء الجلسة وتحديث قائمة الجلسات.',
    revokeError: 'تعذر إلغاء الجلسة. أعد تسجيل الدخول ثم حاول مرة أخرى.',
    setupStarted: 'بدأ إعداد تطبيق المصادقة. أكّد الرمز الحالي المكون من ستة أرقام.',
    setupError: 'تعذر بدء إعداد تطبيق المصادقة. أعد تسجيل الدخول وحاول مرة أخرى.',
    enabled: 'تم تفعيل تطبيق المصادقة. احفظ رموز الاسترداد الآن؛ لن تظهر مرة أخرى.',
    codeError: 'لم يتم قبول الرمز. لم يُجر أي تغيير على تطبيق المصادقة.',
    recoveryReplaced: 'تم استبدال رموز الاسترداد. احفظها الآن؛ لن تظهر مرة أخرى.',
    recoveryError: 'تعذر استبدال رموز الاسترداد. أعد تسجيل الدخول وتحقق من الرمز.',
    mfa: 'المصادقة متعددة العوامل',
    authenticator: 'تطبيق المصادقة',
    authenticatorHelp: 'استخدم كلمة مرور مؤقتة تعتمد على الوقت بعد إعادة تسجيل الدخول.',
    setup: 'إعداد تطبيق المصادقة',
    enrollmentUnavailable: 'الإعداد غير متاح حتى يتم تهيئة تخزين الأسرار المشفر.',
    recovery: 'رموز الاسترداد',
    recoveryHelp: 'تظهر رموز الاسترداد مرة واحدة فقط. احفظها خارج هذا الموقع.',
    recoveryCreated: 'تُنشأ رموز جديدة عند تأكيد إعداد تطبيق المصادقة.',
    currentCode: 'رمز تطبيق المصادقة الحالي',
    replaceRecovery: 'استبدال رموز الاسترداد',
    passkeys: 'مفاتيح المرور',
    addPasskey: 'إضافة مفتاح مرور',
    passkeysUnavailable: 'مفاتيح المرور غير مفعلة لهذا الموقع.',
    confirmAuthenticator: 'تأكيد تطبيق المصادقة',
    setupUri: 'افتح رابط الإعداد هذا في تطبيق المصادقة:',
    sixDigit: 'رمز من ستة أرقام',
    confirm: 'تأكيد تطبيق المصادقة',
    oneTimeCodes: 'رموز استرداد للاستخدام مرة واحدة',
    sessions: 'الجلسات',
    refresh: 'تحديث الجلسات',
    noSessions: 'لا توجد جلسات متاحة.',
    unknownDevice: 'جهاز غير معروف',
    currentSession: 'الجلسة الحالية',
    otherSession: 'جلسة أخرى',
    revoking: 'جارٍ الإلغاء…',
    revoke: 'إلغاء',
  },
};

const AccountCenter = ({ user, embedded = false, locale: requestedLocale = 'en' }) => {
  const locale = Object.prototype.hasOwnProperty.call(ACCOUNT_COPY, requestedLocale)
    ? requestedLocale
    : 'en';
  const copy = ACCOUNT_COPY[locale];
  const [capabilities, setCapabilities] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [loadingError, setLoadingError] = useState('');
  const [status, setStatus] = useState('');
  const [busySession, setBusySession] = useState('');
  const [enrollment, setEnrollment] = useState(null);
  const [totpCode, setTotpCode] = useState('');
  const [recoveryCodes, setRecoveryCodes] = useState([]);
  const [recoveryTotpCode, setRecoveryTotpCode] = useState('');
  const [mfaBusy, setMfaBusy] = useState(false);

  const load = useCallback(async () => {
    setLoadingError('');
    const [capabilityResult, sessionResult] = await Promise.allSettled([
      identityAdminAPI.capabilities(),
      identityAdminAPI.sessions(),
    ]);
    if (capabilityResult.status === 'fulfilled') setCapabilities(capabilityResult.value);
    if (sessionResult.status === 'fulfilled') {
      setSessions(safeList(sessionResult.value?.sessions ?? sessionResult.value));
    }
    if (capabilityResult.status === 'rejected' || sessionResult.status === 'rejected') {
      setLoadingError(copy.loadError);
    }
  }, [copy.loadError]);

  useEffect(() => {
    load();
  }, [load]);

  const revoke = async (session) => {
    setStatus('');
    setBusySession(session.id);
    try {
      await identityAdminAPI.revokeSession(session.id);
      setStatus(copy.revoked);
      await load();
    } catch (_) {
      setLoadingError(copy.revokeError);
    } finally {
      setBusySession('');
    }
  };

  const mfa = capabilities?.mfa;

  const startTotp = async () => {
    setLoadingError('');
    setMfaBusy(true);
    try {
      setEnrollment(await identityAdminAPI.startTotpEnrollment());
      setStatus(copy.setupStarted);
    } catch (_) {
      setLoadingError(copy.setupError);
    } finally {
      setMfaBusy(false);
    }
  };

  const confirmTotp = async () => {
    setLoadingError('');
    setMfaBusy(true);
    try {
      const result = await identityAdminAPI.confirmTotpEnrollment(
        enrollment.authenticator_id,
        totpCode
      );
      setRecoveryCodes(safeList(result?.recovery_codes));
      setEnrollment(null);
      setTotpCode('');
      setStatus(copy.enabled);
    } catch (_) {
      setLoadingError(copy.codeError);
    } finally {
      setMfaBusy(false);
    }
  };

  const regenerateRecovery = async () => {
    setLoadingError('');
    setMfaBusy(true);
    try {
      const result = await identityAdminAPI.regenerateRecoveryCodes(recoveryTotpCode);
      setRecoveryCodes(safeList(result?.recovery_codes));
      setRecoveryTotpCode('');
      setStatus(copy.recoveryReplaced);
    } catch (_) {
      setLoadingError(copy.recoveryError);
    } finally {
      setMfaBusy(false);
    }
  };

  const content = (
    <div
      className="mx-auto max-w-5xl px-4 py-8 space-y-6"
      lang={locale}
      dir={locale === 'ar' ? 'rtl' : 'ltr'}
    >
      {!embedded ? <Navigation /> : null}
      <header className="space-y-1">
        <p className="text-sm opacity-80">{user?.email || ''}</p>
      </header>

      {loadingError ? <div role="alert">{loadingError}</div> : null}
      {status ? <div role="status">{status}</div> : null}

      <section aria-labelledby="mfa-heading" className="space-y-3">
        <h2 id="mfa-heading" className="text-lg font-semibold">
          {copy.mfa}
        </h2>
        <div className="grid gap-4 md:grid-cols-3">
          <GlassCard>
            <div className="p-5 space-y-3">
              <h3 className="font-semibold">{copy.authenticator}</h3>
              <p className="text-sm opacity-80">{copy.authenticatorHelp}</p>
              <GlassButton disabled={!mfa?.totp?.enabled || mfaBusy} onClick={startTotp}>
                {copy.setup}
              </GlassButton>
              {!mfa?.totp?.enabled ? (
                <p className="text-xs opacity-70">{copy.enrollmentUnavailable}</p>
              ) : null}
            </div>
          </GlassCard>
          <GlassCard>
            <div className="p-5 space-y-3">
              <h3 className="font-semibold">{copy.recovery}</h3>
              <p className="text-sm opacity-80">{copy.recoveryHelp}</p>
              <p className="text-xs opacity-70">{copy.recoveryCreated}</p>
              <label htmlFor="recovery-totp-code" className="block text-sm font-medium">
                {copy.currentCode}
              </label>
              <GlassInput
                id="recovery-totp-code"
                value={recoveryTotpCode}
                onChange={(event) =>
                  setRecoveryTotpCode(event.target.value.replace(/\D/g, '').slice(0, 6))
                }
                inputMode="numeric"
                autoComplete="one-time-code"
              />
              <GlassButton
                variant="secondary"
                disabled={!mfa?.recovery_codes?.enabled || recoveryTotpCode.length !== 6 || mfaBusy}
                onClick={regenerateRecovery}
              >
                {copy.replaceRecovery}
              </GlassButton>
            </div>
          </GlassCard>
          <GlassCard>
            <div className="p-5 space-y-3">
              <h3 className="font-semibold">{copy.passkeys}</h3>
              {mfa?.webauthn?.enabled ? (
                <GlassButton>{copy.addPasskey}</GlassButton>
              ) : (
                <p className="text-sm opacity-80">{copy.passkeysUnavailable}</p>
              )}
            </div>
          </GlassCard>
        </div>
        {enrollment ? (
          <GlassCard>
            <div className="p-5 space-y-3">
              <h3 className="font-semibold">{copy.confirmAuthenticator}</h3>
              <p className="text-sm break-all">
                {copy.setupUri} {enrollment.otpauth_uri}
              </p>
              <label htmlFor="totp-code" className="block text-sm font-medium">
                {copy.sixDigit}
              </label>
              <GlassInput
                id="totp-code"
                value={totpCode}
                onChange={(event) => setTotpCode(event.target.value.replace(/\D/g, '').slice(0, 6))}
                inputMode="numeric"
                autoComplete="one-time-code"
              />
              <GlassButton disabled={totpCode.length !== 6 || mfaBusy} onClick={confirmTotp}>
                {copy.confirm}
              </GlassButton>
            </div>
          </GlassCard>
        ) : null}
        {recoveryCodes.length ? (
          <GlassCard>
            <div className="p-5 space-y-3">
              <h3 className="font-semibold">{copy.oneTimeCodes}</h3>
              <ul>
                {recoveryCodes.map((code) => (
                  <li key={code}>
                    <code>{code}</code>
                  </li>
                ))}
              </ul>
            </div>
          </GlassCard>
        ) : null}
      </section>

      <section aria-labelledby="sessions-heading" className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <h2 id="sessions-heading" className="text-lg font-semibold">
            {copy.sessions}
          </h2>
          <GlassButton variant="secondary" onClick={load}>
            {copy.refresh}
          </GlassButton>
        </div>
        {sessions.length === 0 ? <p className="text-sm opacity-80">{copy.noSessions}</p> : null}
        <ul className="space-y-3">
          {sessions.map((session) => {
            const label = session.user_agent || copy.unknownDevice;
            return (
              <li key={session.id}>
                <GlassCard>
                  <div className="p-5 flex flex-wrap items-center justify-between gap-4">
                    <div>
                      <div className="font-medium">{label}</div>
                      <div className="text-sm opacity-70">
                        {session.is_current ? copy.currentSession : copy.otherSession}
                      </div>
                    </div>
                    {!session.is_current ? (
                      <GlassButton
                        variant="ghost"
                        disabled={busySession === session.id}
                        onClick={() => revoke(session)}
                      >
                        {busySession === session.id ? copy.revoking : `${copy.revoke} ${label}`}
                      </GlassButton>
                    ) : null}
                  </div>
                </GlassCard>
              </li>
            );
          })}
        </ul>
      </section>
    </div>
  );

  return embedded ? (
    content
  ) : (
    <AppShell
      headerTitle={copy.shell}
      footerLabel={copy.footer}
      menuLabel={copy.menu}
      themeLabel={copy.theme}
      sidebarLabel={copy.sidebar}
      sidebarItems={copy.sidebarItems}
    >
      {content}
    </AppShell>
  );
};

export default AccountCenter;
