import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import AppShell from '../components/glass/AppShell';
import GlassButton from '../components/glass/GlassButton';
import GlassCard from '../components/glass/GlassCard';
import Navigation from '../components/Navigation';
import { useAuth } from '../contexts/AuthContext';
import { normalizeOperationsError, operationsAPI } from '../services/operations';

const emptySummary = { services: { enabled: 0, total: 0 }, incidents: {}, synthetics24h: {} };
const COPY = {
  en: {
    appShell: 'Application shell',
    themeToggle: 'Toggle color theme',
    privateWorkspace: 'Private workspace',
    menu: 'Menu',
    operationsSummary: 'Operations summary',
    eyebrow: 'Private control plane',
    title: 'Operations center',
    refresh: 'Refresh evidence',
    services: 'Services enabled',
    incidents: 'Open incidents',
    synthetics: 'Synthetic journeys · 24h',
    health: 'Service health',
    recent: 'Recent incidents',
    unavailable: 'Unavailable',
    noServices: 'No services are configured for this site.',
    passed: 'passed',
    failed: 'failed',
    description:
      'Current fleet, release, service, objective, journey, incident, and evidence state for this site.',
    stale: 'Stale evidence',
    partial:
      'Some operations evidence is unavailable. Available panels remain visible and are marked stale when retained.',
    unavailableMessage: 'Operations information is temporarily unavailable.',
    recentAuthRequired: 'Recent authentication is required.',
    reauthenticate: 'Sign in again',
    runtime: 'Runtime delivery',
    jobs: 'Durable jobs',
    ready: 'ready',
    leased: 'leased',
    deadLetters: 'dead letters',
    schedules: 'Schedules',
    enabled: 'enabled',
    late: 'late',
    alerts: 'Alert delivery',
    pending: 'pending',
    terminal: 'terminal',
    fleet: 'Site and fleet',
    site: 'Site',
    releases: 'Releases',
    noRelease: 'No release identity is currently recorded.',
    objectives: 'Objectives',
    noObjectives: 'No objectives are configured.',
    syntheticEvidence: 'Synthetic evidence',
    noSynthetics: 'No synthetic evidence is recorded.',
    latestEvidence: 'Latest evidence',
    observed: 'Observed',
    release: 'Release',
    notRecorded: 'Not recorded',
    noEvidence: 'No evidence yet',
    loading: 'Loading current operations evidence…',
    noIncidents: 'No incidents are currently recorded.',
    owner: 'Owner',
    unassigned: 'Unassigned',
    lastObserved: 'Last observed',
    viewTimeline: 'View timeline',
    opening: 'Opening…',
    acknowledge: 'Acknowledge',
    acknowledging: 'Acknowledging…',
    acknowledgeHelp: 'Acknowledge this incident after reviewing its evidence.',
    acknowledgeConsequence:
      'Acknowledgement assigns the incident to you and records an audit event.',
    timeline: 'Incident timeline',
    closeTimeline: 'Close timeline',
    noTimeline: 'No timeline events are recorded.',
    system: 'System',
    currentSite: 'Current site',
    target: 'Target',
    over: 'over',
    minutes: 'minutes',
    attempts: 'attempts',
    nextRun: 'Next run',
    lastRun: 'Last run',
    missedPolicy: 'Missed policy',
    overlapPolicy: 'Overlap policy',
    errorCode: 'Error',
    replay: 'Replay safely',
    cancel: 'Cancel',
    cancelJob: 'Cancel job',
    cancelTitle: 'Cancel this dead-letter job?',
    cancelConsequence:
      'Cancelling removes this job from the replay queue. This action is audited and cannot be undone here.',
    keepJob: 'Keep job',
    every: 'Every',
    seconds: 'seconds',
    noDeadLetters: 'No dead-letter jobs require review.',
    noSchedules: 'No schedules are configured.',
    noAlerts: 'No alert deliveries are recorded.',
    actionComplete: 'Runtime action completed and evidence refreshed.',
    fleetAndReleases: 'Fleet and releases',
    objectivesAndEvidence: 'Objectives and evidence',
    terms: {},
  },
  de: {
    appShell: 'Anwendungsbereich',
    themeToggle: 'Farbschema wechseln',
    privateWorkspace: 'Privater Arbeitsbereich',
    menu: 'Menü',
    operationsSummary: 'Betriebsübersicht',
    eyebrow: 'Private Steuerung',
    title: 'Betriebszentrale',
    refresh: 'Nachweise aktualisieren',
    services: 'Aktive Dienste',
    incidents: 'Offene Vorfälle',
    synthetics: 'Synthetische Abläufe · 24 Std.',
    health: 'Dienststatus',
    recent: 'Aktuelle Vorfälle',
    unavailable: 'Nicht verfügbar',
    noServices: 'Für diese Website sind keine Dienste konfiguriert.',
    passed: 'bestanden',
    failed: 'fehlgeschlagen',
    description: 'Aktueller Flotten-, Release-, Dienst-, Ziel-, Ablauf- und Vorfallstatus.',
    stale: 'Veraltete Nachweise',
    partial: 'Einige Betriebsnachweise sind nicht verfügbar.',
    unavailableMessage: 'Betriebsinformationen sind vorübergehend nicht verfügbar.',
    recentAuthRequired: 'Eine erneute Anmeldung ist erforderlich.',
    reauthenticate: 'Erneut anmelden',
    runtime: 'Laufzeitzustellung',
    jobs: 'Dauerhafte Aufträge',
    ready: 'bereit',
    leased: 'zugewiesen',
    deadLetters: 'Fehleraufträge',
    schedules: 'Zeitpläne',
    enabled: 'aktiv',
    late: 'verspätet',
    alerts: 'Alarmzustellung',
    pending: 'ausstehend',
    terminal: 'beendet',
    fleet: 'Website und Flotte',
    site: 'Website',
    releases: 'Releases',
    noRelease: 'Keine Release-Identität erfasst.',
    objectives: 'Ziele',
    noObjectives: 'Keine Ziele konfiguriert.',
    syntheticEvidence: 'Synthetische Nachweise',
    noSynthetics: 'Keine synthetischen Nachweise erfasst.',
    latestEvidence: 'Neuester Nachweis',
    observed: 'Beobachtet',
    release: 'Release',
    notRecorded: 'Nicht erfasst',
    noEvidence: 'Noch kein Nachweis',
    loading: 'Betriebsnachweise werden geladen…',
    noIncidents: 'Keine Vorfälle erfasst.',
    owner: 'Verantwortlich',
    unassigned: 'Nicht zugewiesen',
    lastObserved: 'Zuletzt beobachtet',
    viewTimeline: 'Zeitachse anzeigen',
    opening: 'Wird geöffnet…',
    acknowledge: 'Bestätigen',
    acknowledging: 'Wird bestätigt…',
    acknowledgeHelp: 'Nach Prüfung der Nachweise bestätigen.',
    acknowledgeConsequence: 'Die Bestätigung weist den Vorfall zu und wird protokolliert.',
    timeline: 'Vorfallzeitachse',
    closeTimeline: 'Zeitachse schließen',
    noTimeline: 'Keine Zeitachsenereignisse erfasst.',
    system: 'System',
    currentSite: 'Aktuelle Website',
    target: 'Ziel',
    over: 'über',
    minutes: 'Minuten',
    attempts: 'Versuche',
    nextRun: 'Nächster Lauf',
    lastRun: 'Letzter Lauf',
    missedPolicy: 'Versäumnisregel',
    overlapPolicy: 'Überlappungsregel',
    errorCode: 'Fehler',
    replay: 'Sicher wiederholen',
    cancel: 'Abbrechen',
    cancelJob: 'Auftrag abbrechen',
    cancelTitle: 'Diesen Fehlerauftrag abbrechen?',
    cancelConsequence:
      'Der Abbruch entfernt diesen Auftrag aus der Wiederholungswarteschlange. Die Aktion wird protokolliert und kann hier nicht rückgängig gemacht werden.',
    keepJob: 'Auftrag behalten',
    every: 'Alle',
    seconds: 'Sekunden',
    noDeadLetters: 'Keine Fehleraufträge zu prüfen.',
    noSchedules: 'Keine Zeitpläne konfiguriert.',
    noAlerts: 'Keine Alarmzustellungen erfasst.',
    actionComplete: 'Laufzeitaktion abgeschlossen und Nachweise aktualisiert.',
    fleetAndReleases: 'Flotte und Releases',
    objectivesAndEvidence: 'Ziele und Nachweise',
    terms: {
      'operations.collect': 'Betriebsdaten erfassen',
      'operations.health': 'Betriebsstatus',
      'job.attempts_exhausted': 'Maximale Versuche erreicht',
      'provider.transient': 'Vorübergehender Anbieterfehler',
      'api.health': 'API-Status',
      'api.unavailable': 'API nicht verfügbar',
      'worker.queue': 'Arbeitswarteschlange',
      healthy: 'Gesund',
      unknown: 'Unbekannt',
      'api.ready': 'API bereit',
      'probe.no_evidence': 'Kein Prüfnachweis',
      'api.availability': 'API-Verfügbarkeit',
      'member.login': 'Mitgliederanmeldung',
      passed: 'Bestanden',
      'database.unavailable': 'Datenbank nicht verfügbar',
      'certificate.expiring': 'Zertifikat läuft ab',
      'incident.opened': 'Vorfall eröffnet',
      critical: 'Kritisch',
      warning: 'Warnung',
      firing: 'Aktiv',
      acknowledged: 'Bestätigt',
      once: 'Einmal',
      forbid: 'Verhindern',
      retry: 'Wiederholung',
      staging: 'Testumgebung',
      system: 'System',
    },
  },
  ar: {
    appShell: 'مساحة التطبيق',
    themeToggle: 'تبديل سمة الألوان',
    privateWorkspace: 'مساحة عمل خاصة',
    menu: 'القائمة',
    operationsSummary: 'ملخص العمليات',
    eyebrow: 'لوحة تحكم خاصة',
    title: 'مركز العمليات',
    refresh: 'تحديث الأدلة',
    services: 'الخدمات المفعلة',
    incidents: 'الحوادث المفتوحة',
    synthetics: 'الرحلات الاصطناعية · 24 ساعة',
    health: 'حالة الخدمات',
    recent: 'الحوادث الأخيرة',
    unavailable: 'غير متاح',
    noServices: 'لا توجد خدمات مهيأة لهذا الموقع.',
    passed: 'ناجحة',
    failed: 'فاشلة',
    description: 'الحالة الحالية للأسطول والإصدارات والخدمات والأهداف والرحلات والحوادث والأدلة.',
    stale: 'أدلة قديمة',
    partial: 'بعض أدلة العمليات غير متاحة.',
    unavailableMessage: 'معلومات العمليات غير متاحة مؤقتاً.',
    recentAuthRequired: 'يلزم تسجيل الدخول مجدداً.',
    reauthenticate: 'تسجيل الدخول مجدداً',
    runtime: 'تسليم وقت التشغيل',
    jobs: 'المهام الدائمة',
    ready: 'جاهزة',
    leased: 'قيد التنفيذ',
    deadLetters: 'مهام فاشلة',
    schedules: 'الجداول',
    enabled: 'مفعلة',
    late: 'متأخرة',
    alerts: 'تسليم التنبيهات',
    pending: 'معلقة',
    terminal: 'منتهية',
    fleet: 'الموقع والأسطول',
    site: 'الموقع',
    releases: 'الإصدارات',
    noRelease: 'لا توجد هوية إصدار مسجلة.',
    objectives: 'الأهداف',
    noObjectives: 'لا توجد أهداف مهيأة.',
    syntheticEvidence: 'الأدلة الاصطناعية',
    noSynthetics: 'لا توجد أدلة اصطناعية مسجلة.',
    latestEvidence: 'أحدث دليل',
    observed: 'وقت الرصد',
    release: 'الإصدار',
    notRecorded: 'غير مسجل',
    noEvidence: 'لا يوجد دليل بعد',
    loading: 'جارٍ تحميل أدلة العمليات…',
    noIncidents: 'لا توجد حوادث مسجلة.',
    owner: 'المسؤول',
    unassigned: 'غير معيّن',
    lastObserved: 'آخر رصد',
    viewTimeline: 'عرض التسلسل الزمني',
    opening: 'جارٍ الفتح…',
    acknowledge: 'إقرار',
    acknowledging: 'جارٍ الإقرار…',
    acknowledgeHelp: 'أقر بالحادث بعد مراجعة أدلته.',
    acknowledgeConsequence: 'يؤدي الإقرار إلى تعيين الحادث لك وتسجيل حدث تدقيق.',
    timeline: 'التسلسل الزمني للحادث',
    closeTimeline: 'إغلاق التسلسل',
    noTimeline: 'لا توجد أحداث في التسلسل.',
    system: 'النظام',
    currentSite: 'الموقع الحالي',
    target: 'الهدف',
    over: 'خلال',
    minutes: 'دقيقة',
    attempts: 'محاولات',
    nextRun: 'التشغيل التالي',
    lastRun: 'التشغيل الأخير',
    missedPolicy: 'سياسة الفوات',
    overlapPolicy: 'سياسة التداخل',
    errorCode: 'الخطأ',
    replay: 'إعادة آمنة',
    cancel: 'إلغاء',
    cancelJob: 'إلغاء المهمة',
    cancelTitle: 'هل تريد إلغاء هذه المهمة الفاشلة؟',
    cancelConsequence:
      'يؤدي الإلغاء إلى إزالة المهمة من قائمة إعادة المحاولة. يُسجل هذا الإجراء ولا يمكن التراجع عنه من هنا.',
    keepJob: 'إبقاء المهمة',
    every: 'كل',
    seconds: 'ثانية',
    noDeadLetters: 'لا توجد مهام فاشلة للمراجعة.',
    noSchedules: 'لا توجد جداول مهيأة.',
    noAlerts: 'لا توجد عمليات تسليم تنبيه.',
    actionComplete: 'اكتمل الإجراء وتم تحديث الأدلة.',
    fleetAndReleases: 'المواقع والإصدارات',
    objectivesAndEvidence: 'الأهداف والأدلة',
    terms: {
      'operations.collect': 'جمع بيانات العمليات',
      'operations.health': 'صحة العمليات',
      'job.attempts_exhausted': 'استُنفدت المحاولات',
      'provider.transient': 'خطأ مؤقت لدى المزود',
      'api.health': 'صحة الواجهة البرمجية',
      'api.unavailable': 'الواجهة البرمجية غير متاحة',
      'worker.queue': 'قائمة انتظار العامل',
      healthy: 'سليمة',
      unknown: 'غير معروفة',
      'api.ready': 'الواجهة جاهزة',
      'probe.no_evidence': 'لا يوجد دليل فحص',
      'api.availability': 'توفر الواجهة البرمجية',
      'member.login': 'تسجيل دخول العضو',
      passed: 'ناجح',
      'database.unavailable': 'قاعدة البيانات غير متاحة',
      'certificate.expiring': 'الشهادة قاربت الانتهاء',
      'incident.opened': 'فُتح الحادث',
      critical: 'حرج',
      warning: 'تحذير',
      firing: 'نشط',
      acknowledged: 'تم الإقرار',
      once: 'مرة واحدة',
      forbid: 'منع',
      retry: 'إعادة المحاولة',
      staging: 'بيئة الاختبار',
      system: 'النظام',
    },
  },
};

export default function OperationsCenter() {
  const { user } = useAuth();
  const requestedLocale = String(user?.locale || document.documentElement.lang || 'en').split(
    '-'
  )[0];
  const locale = Object.prototype.hasOwnProperty.call(COPY, requestedLocale)
    ? requestedLocale
    : 'en';
  const copy = COPY[locale];
  const direction = locale === 'ar' ? 'rtl' : 'ltr';
  const [summary, setSummary] = useState(emptySummary);
  const [overview, setOverview] = useState({
    site: {},
    releases: [],
    services: [],
    objectives: [],
    synthetics: [],
  });
  const [incidents, setIncidents] = useState([]);
  const [evidence, setEvidence] = useState({
    summary: 'unavailable',
    overview: 'unavailable',
    incidents: 'unavailable',
  });
  const [selectedIncident, setSelectedIncident] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');
  const [pending, setPending] = useState('');
  const [recentAuthRequired, setRecentAuthRequired] = useState(false);
  const [cancelCandidate, setCancelCandidate] = useState(null);
  const timelineHeading = useRef(null);
  const timelineTrigger = useRef(null);
  const cancelHeading = useRef(null);
  const cancelTrigger = useRef(null);
  const cancelDialog = useRef(null);

  const presentError = useCallback(
    (reason) => {
      const normalized = normalizeOperationsError(reason);
      const reauthentication = normalized.message.startsWith('Recent authentication');
      setRecentAuthRequired(reauthentication);
      setError(reauthentication ? copy.recentAuthRequired : copy.unavailableMessage);
    },
    [copy.recentAuthRequired, copy.unavailableMessage]
  );

  const load = useCallback(
    async (signal) => {
      setLoading(true);
      setError('');
      setRecentAuthRequired(false);
      const results = await Promise.allSettled([
        operationsAPI.summary({ signal }),
        operationsAPI.incidents({ signal }),
        operationsAPI.overview({ signal }),
      ]);
      if (signal?.aborted) return;
      const names = ['summary', 'incidents', 'overview'];
      setEvidence((previous) => {
        const next = { ...previous };
        results.forEach((result, index) => {
          next[names[index]] =
            result.status === 'fulfilled'
              ? 'fresh'
              : previous[names[index]] === 'fresh'
                ? 'stale'
                : previous[names[index]];
        });
        return next;
      });
      if (results[0].status === 'fulfilled') setSummary(results[0].value || emptySummary);
      if (results[1].status === 'fulfilled') {
        setIncidents(Array.isArray(results[1].value?.incidents) ? results[1].value.incidents : []);
      }
      if (results[2].status === 'fulfilled') setOverview(results[2].value || {});
      const rejection = results.find((result) => result.status === 'rejected');
      if (rejection) presentError(rejection.reason);
      setLoading(false);
    },
    [presentError]
  );

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, [load]);

  useEffect(() => {
    const prior = { lang: document.documentElement.lang, dir: document.documentElement.dir };
    document.documentElement.lang = locale;
    document.documentElement.dir = direction;
    return () => {
      document.documentElement.lang = prior.lang;
      document.documentElement.dir = prior.dir;
    };
  }, [direction, locale]);

  const acknowledge = async (incidentId) => {
    setPending(incidentId);
    setError('');
    setRecentAuthRequired(false);
    try {
      await operationsAPI.acknowledge(incidentId);
      setStatus(copy.actionComplete);
      await load();
    } catch (caught) {
      presentError(caught);
    } finally {
      setPending('');
    }
  };

  const actOnDeadLetter = async (jobId, action) => {
    setPending(`job:${jobId}`);
    setError('');
    setRecentAuthRequired(false);
    setStatus('');
    try {
      await operationsAPI.actOnDeadLetter(jobId, action);
      setStatus(copy.actionComplete);
      await load();
    } catch (caught) {
      presentError(caught);
    } finally {
      setPending('');
    }
  };

  useEffect(() => {
    if (!cancelCandidate) return undefined;
    window.requestAnimationFrame(() => cancelHeading.current?.focus());
    const onKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        setCancelCandidate(null);
        window.setTimeout(() => cancelTrigger.current?.focus(), 0);
        return;
      }
      if (event.key !== 'Tab') return;
      const controls = Array.from(cancelDialog.current?.querySelectorAll('button') || []).filter(
        (control) => !control.disabled
      );
      if (!controls.length) return;
      const first = controls[0];
      const last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [cancelCandidate]);

  const closeCancelConfirmation = () => {
    setCancelCandidate(null);
    window.setTimeout(() => cancelTrigger.current?.focus(), 0);
  };

  const confirmCancel = async () => {
    const jobId = cancelCandidate?.jobId;
    if (!jobId) return;
    setCancelCandidate(null);
    await actOnDeadLetter(jobId, 'cancel');
    window.setTimeout(() => cancelTrigger.current?.focus(), 0);
  };

  const inspectIncident = async (incidentId, trigger) => {
    timelineTrigger.current = trigger;
    setPending(`inspect:${incidentId}`);
    setError('');
    setRecentAuthRequired(false);
    try {
      const result = await operationsAPI.incident(incidentId);
      setSelectedIncident(result?.incident || null);
      window.requestAnimationFrame(() => timelineHeading.current?.focus());
    } catch (caught) {
      presentError(caught);
    } finally {
      setPending('');
    }
  };

  const canManage = Boolean(user?.permissions?.includes('operations.manage'));
  const formatDate = (value) => {
    if (!value) return copy.noEvidence;
    try {
      return new Intl.DateTimeFormat(locale, {
        dateStyle: 'medium',
        timeStyle: 'short',
        timeZone: user?.timezone || 'UTC',
      }).format(new Date(value));
    } catch (_) {
      return new Intl.DateTimeFormat(locale, {
        dateStyle: 'medium',
        timeStyle: 'short',
        timeZone: 'UTC',
      }).format(new Date(value));
    }
  };
  const readable = (value) => {
    const normalized = String(value || 'unknown').toLowerCase();
    if (copy.terms?.[normalized]) return copy.terms[normalized];
    if (normalized.startsWith('every:')) {
      return `${copy.every} ${normalized.slice('every:'.length)} ${copy.seconds}`;
    }
    return String(value || 'unknown')
      .replace(/[._-]+/g, ' ')
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
  };

  const openIncidents = Object.values(summary.incidents || {}).reduce(
    (total, value) => total + Number(value || 0),
    0
  );
  const syntheticPassed = Number(summary.synthetics24h?.passed || 0);
  const syntheticFailed = Number(summary.synthetics24h?.failed || 0);
  const available = (name) => evidence[name] !== 'unavailable';
  const summaryValue = (value) => (available('summary') ? value : copy.unavailable);
  const evidenceLabel = (name) => (evidence[name] === 'stale' ? copy.stale : null);

  return (
    <AppShell
      headerTitle={copy.appShell}
      headerIsPageHeading={false}
      footerLabel={copy.privateWorkspace}
      menuLabel={copy.menu}
      themeLabel={copy.themeToggle}
    >
      <Navigation />
      <div
        className="operations-center mx-auto w-full max-w-6xl px-4 py-8"
        aria-busy={loading}
        lang={locale}
        dir={direction}
      >
        <style>{`
          @media (prefers-reduced-motion: reduce) {
            .operations-center *,
            .operations-center *::before,
            .operations-center *::after {
              animation-duration: 0s !important;
              scroll-behavior: auto !important;
              transition-duration: 0s !important;
            }
          }
        `}</style>
        <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-sm uppercase tracking-[0.18em] opacity-70">{copy.eyebrow}</p>
            <h1 className="text-3xl font-semibold">{copy.title}</h1>
            <p className="mt-2 max-w-2xl opacity-80">{copy.description}</p>
          </div>
          <GlassButton type="button" variant="ghost" onClick={() => load()} disabled={loading}>
            {copy.refresh}
          </GlassButton>
        </header>

        {error ? (
          <div role="alert" className="mb-5 rounded-xl border border-red-400/50 p-4">
            {error}
            {recentAuthRequired ? (
              <Link className="ms-2 underline" to="/login?next=%2Foperations">
                {copy.reauthenticate}
              </Link>
            ) : null}
          </div>
        ) : null}
        {status ? (
          <div role="status" className="mb-5 rounded-xl border border-emerald-400/50 p-4">
            {status}
          </div>
        ) : null}

        <section aria-label={copy.operationsSummary} className="mt-4">
          {evidenceLabel('summary') ? <p role="status">{evidenceLabel('summary')}</p> : null}
          <div className="mt-4 grid gap-4 sm:grid-cols-3">
            <GlassCard className="p-5">
              <p className="text-sm opacity-70">{copy.services}</p>
              <p className="mt-2 text-3xl font-semibold">
                {summaryValue(`${summary.services?.enabled || 0}/${summary.services?.total || 0}`)}
              </p>
            </GlassCard>
            <GlassCard className="p-5">
              <p className="text-sm opacity-70">{copy.incidents}</p>
              <p className="mt-2 text-3xl font-semibold">{summaryValue(openIncidents)}</p>
            </GlassCard>
            <GlassCard className="p-5">
              <p className="text-sm opacity-70">{copy.synthetics}</p>
              <p className="mt-2 text-3xl font-semibold">
                {summaryValue(`${syntheticPassed} ${copy.passed}`)}
              </p>
              {available('summary') ? (
                <p className="text-sm opacity-70">
                  {syntheticFailed} {copy.failed}
                </p>
              ) : null}
            </GlassCard>
          </div>
        </section>

        <section className="mt-8" aria-labelledby="runtime-heading">
          <h2 id="runtime-heading" className="text-xl font-semibold">
            {copy.runtime}
          </h2>
          {available('overview') ? (
            <div className="mt-4 space-y-4">
              {evidenceLabel('overview') ? <p role="status">{evidenceLabel('overview')}</p> : null}
              <div className="grid gap-3 sm:grid-cols-3">
                <GlassCard className="p-5">
                  <h3 className="font-semibold">{copy.jobs}</h3>
                  <p className="mt-2 text-sm">
                    {overview.runtime?.jobs?.ready || 0} {copy.ready} ·{' '}
                    {overview.runtime?.jobs?.leased || 0} {copy.leased}
                  </p>
                  <p className="text-sm opacity-70">
                    {overview.runtime?.jobs?.deadLetters || 0} {copy.deadLetters}
                  </p>
                </GlassCard>
                <GlassCard className="p-5">
                  <h3 className="font-semibold">{copy.schedules}</h3>
                  <p className="mt-2 text-sm">
                    {overview.runtime?.schedules?.enabled || 0} {copy.enabled}
                  </p>
                  <p className="text-sm opacity-70">
                    {overview.runtime?.schedules?.late || 0} {copy.late}
                  </p>
                </GlassCard>
                <GlassCard className="p-5">
                  <h3 className="font-semibold">{copy.alerts}</h3>
                  <p className="mt-2 text-sm">
                    {overview.runtime?.alerts?.pending || 0} {copy.pending}
                  </p>
                  <p className="text-sm opacity-70">
                    {overview.runtime?.alerts?.terminal || 0} {copy.terminal}
                  </p>
                </GlassCard>
              </div>
              <div className="grid gap-3 lg:grid-cols-3">
                <GlassCard className="p-5">
                  <h3 className="font-semibold">{copy.deadLetters}</h3>
                  {overview.runtime?.jobs?.items?.length ? (
                    <ul className="mt-3 space-y-4">
                      {overview.runtime.jobs.items.map((job) => (
                        <li key={job.jobId}>
                          <p className="font-medium">{readable(job.jobType)}</p>
                          <p className="text-sm opacity-70">
                            {job.attempts}/{job.maximumAttempts} {copy.attempts} · {copy.errorCode}:{' '}
                            {readable(job.errorCode)}
                          </p>
                          <p className="text-sm opacity-70">{formatDate(job.updatedAt)}</p>
                          {canManage ? (
                            <div className="mt-2 flex flex-wrap gap-2">
                              <GlassButton
                                type="button"
                                variant="secondary"
                                disabled={Boolean(pending)}
                                onClick={() => actOnDeadLetter(job.jobId, 'replay')}
                              >
                                {copy.replay}
                              </GlassButton>
                              <GlassButton
                                type="button"
                                variant="ghost"
                                disabled={Boolean(pending)}
                                onClick={(event) => {
                                  cancelTrigger.current = event.currentTarget;
                                  setCancelCandidate(job);
                                }}
                              >
                                {copy.cancel}
                              </GlassButton>
                            </div>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-3 opacity-70">{copy.noDeadLetters}</p>
                  )}
                </GlassCard>
                <GlassCard className="p-5">
                  <h3 className="font-semibold">{copy.schedules}</h3>
                  {overview.runtime?.schedules?.items?.length ? (
                    <ul className="mt-3 space-y-4">
                      {overview.runtime.schedules.items.map((schedule) => (
                        <li key={schedule.scheduleId}>
                          <p className="font-medium">{readable(schedule.scheduleKey)}</p>
                          <p className="text-sm opacity-70">
                            {schedule.timezone} · {readable(schedule.rule)}
                          </p>
                          <p className="text-sm opacity-70">
                            {copy.nextRun}: {formatDate(schedule.nextRunAt)} · {copy.lastRun}:{' '}
                            {formatDate(schedule.lastRunAt)}
                          </p>
                          <p className="text-sm opacity-70">
                            {copy.missedPolicy}: {readable(schedule.missedPolicy)} ·{' '}
                            {copy.overlapPolicy}: {readable(schedule.overlapPolicy)}
                          </p>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-3 opacity-70">{copy.noSchedules}</p>
                  )}
                </GlassCard>
                <GlassCard className="p-5">
                  <h3 className="font-semibold">{copy.alerts}</h3>
                  {overview.runtime?.alerts?.items?.length ? (
                    <ul className="mt-3 space-y-4">
                      {overview.runtime.alerts.items.map((alert) => (
                        <li key={alert.deliveryId}>
                          <p className="font-medium">{readable(alert.status)}</p>
                          <p className="text-sm opacity-70">
                            {alert.attempts}/{alert.maximumAttempts} {copy.attempts}
                            {alert.errorCode
                              ? ` · ${copy.errorCode}: ${readable(alert.errorCode)}`
                              : ''}
                          </p>
                          <p className="text-sm opacity-70">{formatDate(alert.updatedAt)}</p>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-3 opacity-70">{copy.noAlerts}</p>
                  )}
                </GlassCard>
              </div>
            </div>
          ) : (
            <GlassCard className="mt-4 p-5">
              <p>{copy.unavailable}</p>
            </GlassCard>
          )}
        </section>

        <section className="mt-8 grid gap-4 lg:grid-cols-2" aria-label={copy.fleetAndReleases}>
          <GlassCard className="p-5">
            <h2 className="text-xl font-semibold">{copy.fleet}</h2>
            {!available('overview') ? (
              <p className="mt-4">{copy.unavailable}</p>
            ) : (
              <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
                <div>
                  <dt className="opacity-70">{copy.site}</dt>
                  <dd className="font-medium">{overview.site?.id || copy.currentSite}</dd>
                </div>
                <div>
                  <dt className="opacity-70">{copy.services}</dt>
                  <dd className="font-medium">{overview.site?.serviceCount || 0}</dd>
                </div>
              </dl>
            )}
          </GlassCard>
          <GlassCard className="p-5">
            <h2 className="text-xl font-semibold">{copy.releases}</h2>
            {!available('overview') ? (
              <p className="mt-4">{copy.unavailable}</p>
            ) : overview.releases?.length ? (
              <ul className="mt-4 space-y-2">
                {overview.releases.map((release) => (
                  <li key={release} className="break-all font-mono text-sm">
                    {release}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-4 opacity-70">{copy.noRelease}</p>
            )}
          </GlassCard>
        </section>

        <section className="mt-8" aria-labelledby="services-heading">
          <h2 id="services-heading" className="text-xl font-semibold">
            {copy.health}
          </h2>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {!available('overview') ? (
              <GlassCard className="p-5">
                <p>{copy.unavailable}</p>
              </GlassCard>
            ) : (
              overview.services?.map((service) => (
                <GlassCard key={service.id} className="p-5">
                  <div className="flex flex-wrap justify-between gap-3">
                    <div>
                      <h3 className="font-semibold">{readable(service.serviceKey)}</h3>
                      <p className="text-sm opacity-70">{readable(service.environment)}</p>
                    </div>
                    <span className="rounded-full border px-3 py-1 text-xs font-medium">
                      {readable(service.health?.state)}
                    </span>
                  </div>
                  <dl className="mt-4 grid gap-2 text-sm">
                    <div>
                      <dt className="opacity-70">{copy.latestEvidence}</dt>
                      <dd>{readable(service.health?.code)}</dd>
                    </div>
                    <div>
                      <dt className="opacity-70">{copy.observed}</dt>
                      <dd>{formatDate(service.health?.observedAt)}</dd>
                    </div>
                    <div>
                      <dt className="opacity-70">{copy.release}</dt>
                      <dd className="break-all font-mono">
                        {service.releaseId || copy.notRecorded}
                      </dd>
                    </div>
                  </dl>
                </GlassCard>
              ))
            )}
            {!loading && available('overview') && !overview.services?.length ? (
              <GlassCard className="p-5">
                <p>{copy.noServices}</p>
              </GlassCard>
            ) : null}
          </div>
        </section>

        <section className="mt-8 grid gap-4 lg:grid-cols-2" aria-label={copy.objectivesAndEvidence}>
          <GlassCard className="p-5">
            <h2 className="text-xl font-semibold">{copy.objectives}</h2>
            {!available('overview') ? (
              <p className="mt-4">{copy.unavailable}</p>
            ) : overview.objectives?.length ? (
              <ul className="mt-4 space-y-3">
                {overview.objectives.map((objective) => (
                  <li key={objective.objectiveKey}>
                    <p className="font-medium">{readable(objective.objectiveKey)}</p>
                    <p className="text-sm opacity-70">
                      {copy.target} {(Number(objective.target) * 100).toFixed(2)}% {copy.over}{' '}
                      {objective.windowMinutes} {copy.minutes}
                    </p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-4 opacity-70">{copy.noObjectives}</p>
            )}
          </GlassCard>
          <GlassCard className="p-5">
            <h2 className="text-xl font-semibold">{copy.syntheticEvidence}</h2>
            {!available('overview') ? (
              <p className="mt-4">{copy.unavailable}</p>
            ) : overview.synthetics?.length ? (
              <ul className="mt-4 space-y-3">
                {overview.synthetics.map((run) => (
                  <li key={run.id}>
                    <p className="font-medium">{readable(run.journeyKey)}</p>
                    <p className="text-sm opacity-70">
                      {readable(run.status)} · {formatDate(run.startedAt)}
                    </p>
                    <p className="mt-1 break-all font-mono text-xs opacity-70">
                      {copy.release} {run.sourceCommit}
                    </p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-4 opacity-70">{copy.noSynthetics}</p>
            )}
          </GlassCard>
        </section>

        <section className="mt-8" aria-labelledby="incident-heading">
          <h2 id="incident-heading" className="text-xl font-semibold">
            {copy.recent}
          </h2>
          {evidenceLabel('incidents') ? (
            <p className="mt-4" role="status">
              {evidenceLabel('incidents')}
            </p>
          ) : null}
          {loading ? (
            <p role="status" className="mt-4">
              {copy.loading}
            </p>
          ) : null}
          {!loading && available('incidents') && incidents.length === 0 ? (
            <GlassCard className="mt-4 p-5">
              <p>{copy.noIncidents}</p>
            </GlassCard>
          ) : null}
          {!loading && !available('incidents') ? (
            <GlassCard className="mt-4 p-5">
              <p>{copy.unavailable}</p>
            </GlassCard>
          ) : null}
          <div className="mt-4 grid gap-3">
            {incidents.map((incident) => (
              <GlassCard key={incident.id} className="p-5">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-wider opacity-70">
                      {readable(incident.severity)} · {readable(incident.state)}
                    </p>
                    <h3 className="mt-1 font-semibold">{readable(incident.summaryCode)}</h3>
                    <p className="mt-1 text-sm opacity-70">
                      {copy.observed}: {incident.occurrenceCount}
                    </p>
                    <p className="mt-1 text-sm opacity-70">
                      {copy.lastObserved} {formatDate(incident.lastObservedAt)}
                    </p>
                    <p className="mt-1 text-sm opacity-70">
                      {copy.owner} {incident.ownerRef || copy.unassigned}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <GlassButton
                      type="button"
                      variant="ghost"
                      onClick={(event) => inspectIncident(incident.id, event.currentTarget)}
                      disabled={Boolean(pending)}
                    >
                      {pending === `inspect:${incident.id}` ? copy.opening : copy.viewTimeline}
                    </GlassButton>
                    {canManage && ['firing', 'recurring'].includes(incident.state) ? (
                      <GlassButton
                        type="button"
                        onClick={() => acknowledge(incident.id)}
                        disabled={Boolean(pending)}
                        aria-describedby={`incident-${incident.id}`}
                      >
                        {pending === incident.id ? copy.acknowledging : copy.acknowledge}
                      </GlassButton>
                    ) : null}
                  </div>
                </div>
                <span id={`incident-${incident.id}`} className="sr-only">
                  {copy.acknowledgeHelp}
                </span>
                {canManage && ['firing', 'recurring'].includes(incident.state) ? (
                  <p className="mt-3 text-sm opacity-70">{copy.acknowledgeConsequence}</p>
                ) : null}
              </GlassCard>
            ))}
          </div>
        </section>

        {selectedIncident ? (
          <section className="mt-8" aria-labelledby="timeline-heading">
            <GlassCard className="p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2
                    id="timeline-heading"
                    className="text-xl font-semibold"
                    ref={timelineHeading}
                    tabIndex={-1}
                  >
                    {copy.timeline}
                  </h2>
                  <p className="mt-1 opacity-70">{readable(selectedIncident.summaryCode)}</p>
                </div>
                <GlassButton
                  type="button"
                  variant="ghost"
                  onClick={() => {
                    setSelectedIncident(null);
                    window.setTimeout(() => timelineTrigger.current?.focus(), 0);
                  }}
                >
                  {copy.closeTimeline}
                </GlassButton>
              </div>
              {selectedIncident.timeline?.length ? (
                <ol className="mt-5 space-y-4 border-s border-white/20 ps-5">
                  {selectedIncident.timeline.map((event) => (
                    <li key={event.id}>
                      <p className="font-medium">{readable(event.eventKey)}</p>
                      <p className="text-sm opacity-70">
                        {formatDate(event.occurredAt)} · {readable(event.actorRef || 'system')}
                      </p>
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="mt-4 opacity-70">{copy.noTimeline}</p>
              )}
            </GlassCard>
          </section>
        ) : null}

        {cancelCandidate ? (
          <div
            ref={cancelDialog}
            className="fixed inset-0 z-[70] grid place-items-center bg-black/60 p-4"
            role="dialog"
            aria-modal="true"
            aria-labelledby="cancel-job-heading"
            aria-describedby="cancel-job-consequence"
          >
            <GlassCard className="w-full max-w-lg p-6">
              <h2
                id="cancel-job-heading"
                ref={cancelHeading}
                tabIndex={-1}
                className="text-xl font-semibold"
              >
                {copy.cancelTitle}
              </h2>
              <p id="cancel-job-consequence" className="mt-3 opacity-80">
                {copy.cancelConsequence}
              </p>
              <p className="mt-3 text-sm opacity-70">{readable(cancelCandidate.jobType)}</p>
              <div className="mt-6 flex flex-wrap justify-end gap-3">
                <GlassButton type="button" variant="ghost" onClick={closeCancelConfirmation}>
                  {copy.keepJob}
                </GlassButton>
                <GlassButton type="button" variant="danger" onClick={confirmCancel}>
                  {copy.cancelJob}
                </GlassButton>
              </div>
            </GlassCard>
          </div>
        ) : null}
      </div>
    </AppShell>
  );
}
