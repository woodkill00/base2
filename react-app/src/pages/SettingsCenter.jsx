import { useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  Bell,
  Building2,
  ChevronRight,
  Code2,
  Eye,
  Globe2,
  LayoutGrid,
  LockKeyhole,
  Search,
  ShieldCheck,
  UserRound,
} from 'lucide-react';

import AppShell from '../components/glass/AppShell';
import GlassButton from '../components/glass/GlassButton';
import GlassCard from '../components/glass/GlassCard';
import GlassInput from '../components/glass/GlassInput';
import Navigation from '../components/Navigation';
import AccountCenter from './AccountCenter';
import { useAuth } from '../contexts/AuthContext';
import apiClient from '../lib/apiClient';
import { normalizeApiError } from '../lib/apiErrors';
import { settingsAPI } from '../services/settings';

const FALLBACK_CATEGORIES = [
  ['overview', 'Overview', 'Account health and recommended actions', LayoutGrid, '/settings'],
  ['profile', 'Profile', 'Identity and public information', UserRound, '/settings/profile'],
  [
    'security',
    'Sign-in & security',
    'Authentication, recovery, devices, and sessions',
    ShieldCheck,
    '/settings/security',
  ],
  [
    'privacy',
    'Privacy & data',
    'Consent, exports, corrections, and deletion',
    LockKeyhole,
    '/settings/privacy',
  ],
  [
    'notifications',
    'Notifications',
    'Security, product, and marketing delivery',
    Bell,
    '/settings/notifications',
  ],
  [
    'appearance',
    'Appearance & accessibility',
    'Theme, contrast, motion, and density',
    Eye,
    '/settings/appearance',
  ],
  [
    'language-region',
    'Language & region',
    'Locale, time zone, and week format',
    Globe2,
    '/settings/language-region',
  ],
  [
    'organization',
    'Organization',
    'Members, roles, invitations, and audit controls',
    Building2,
    '/settings/organization',
  ],
  [
    'developer',
    'Developer',
    'API documentation and integration credentials',
    Code2,
    '/settings/developer',
  ],
].map(([id, label, description, icon, path]) => ({
  id,
  label,
  description,
  icon,
  path,
  synonyms:
    {
      security: 'password mfa passkey login device session recovery',
      privacy: 'consent export correction deactivate delete data',
      notifications: 'email alerts messages digest marketing',
      appearance: 'theme dark light contrast motion accessibility density',
      'language-region': 'locale timezone time zone date week',
      organization: 'team members roles invites audit',
      developer: 'api docs tokens credentials integration',
    }[id] || '',
}));

const DEFAULT_NOTIFICATIONS = [
  { event_family: 'security', channel: 'email', delivery: 'immediate', mandatory: true },
  { event_family: 'transactional', channel: 'email', delivery: 'immediate', mandatory: true },
  { event_family: 'product', channel: 'email', delivery: 'digest', mandatory: false },
  { event_family: 'marketing', channel: 'email', delivery: 'disabled', mandatory: false },
];

const preferenceDefaults = {
  version: 0,
  theme: 'system',
  contrast: 'system',
  motion: 'system',
  density: 'comfortable',
  locale: 'en',
  timezone: 'UTC',
  week_start: 'system',
};

const SETTINGS_COPY = {
  en: {
    appShell: 'Settings',
    themeToggle: 'Toggle color theme',
    privateWorkspace: 'Private workspace',
    menu: 'Menu',
    sidebar: 'Sidebar',
    sidebarItems: ['Home', 'Dashboard', 'Settings', 'Users', 'Help'],
    breadcrumb: 'Breadcrumb',
    settings: 'Settings',
    controlCenter: 'Account control center',
    search: 'Search settings',
    categories: 'Settings categories',
    noResults: 'No settings found.',
    details: 'details',
    loading: 'Loading settings…',
    language: 'Language',
    timezone: 'Time zone',
    weekStart: 'Week starts on',
    systemDefault: 'System default',
    monday: 'Monday',
    sunday: 'Sunday',
    saturday: 'Saturday',
    saving: 'Saving…',
    savePreferences: 'Save preferences',
  },
  de: {
    appShell: 'Einstellungen',
    themeToggle: 'Farbschema wechseln',
    privateWorkspace: 'Privater Arbeitsbereich',
    menu: 'Menü',
    sidebar: 'Seitenleiste',
    sidebarItems: ['Start', 'Übersicht', 'Einstellungen', 'Benutzer', 'Hilfe'],
    breadcrumb: 'Brotkrümelnavigation',
    settings: 'Einstellungen',
    controlCenter: 'Kontozentrale',
    search: 'Einstellungen durchsuchen',
    categories: 'Einstellungskategorien',
    noResults: 'Keine Einstellungen gefunden.',
    details: 'Details',
    loading: 'Einstellungen werden geladen…',
    language: 'Sprache',
    timezone: 'Zeitzone',
    weekStart: 'Wochenbeginn',
    systemDefault: 'Systemstandard',
    monday: 'Montag',
    sunday: 'Sonntag',
    saturday: 'Samstag',
    saving: 'Speichern…',
    savePreferences: 'Einstellungen speichern',
  },
  ar: {
    appShell: 'الإعدادات',
    themeToggle: 'تبديل سمة الألوان',
    privateWorkspace: 'مساحة عمل خاصة',
    menu: 'القائمة',
    sidebar: 'الشريط الجانبي',
    sidebarItems: ['الرئيسية', 'لوحة المعلومات', 'الإعدادات', 'المستخدمون', 'المساعدة'],
    breadcrumb: 'مسار التنقل',
    settings: 'الإعدادات',
    controlCenter: 'مركز التحكم بالحساب',
    search: 'البحث في الإعدادات',
    categories: 'فئات الإعدادات',
    noResults: 'لم يتم العثور على إعدادات.',
    details: 'التفاصيل',
    loading: 'جارٍ تحميل الإعدادات…',
    language: 'اللغة',
    timezone: 'المنطقة الزمنية',
    weekStart: 'بداية الأسبوع',
    systemDefault: 'إعداد النظام',
    monday: 'الاثنين',
    sunday: 'الأحد',
    saturday: 'السبت',
    saving: 'جارٍ الحفظ…',
    savePreferences: 'حفظ التفضيلات',
  },
};

const CATEGORY_COPY = {
  de: {
    overview: ['Übersicht', 'Kontostatus und empfohlene Aktionen'],
    profile: ['Profil', 'Identität und öffentliche Informationen'],
    security: [
      'Anmeldung und Sicherheit',
      'Authentifizierung, Wiederherstellung, Geräte und Sitzungen',
    ],
    privacy: ['Datenschutz und Daten', 'Einwilligungen, Exporte, Korrekturen und Löschung'],
    notifications: ['Benachrichtigungen', 'Sicherheits-, Produkt- und Marketingzustellung'],
    appearance: ['Darstellung und Barrierefreiheit', 'Design, Kontrast, Bewegung und Dichte'],
    'language-region': ['Sprache und Region', 'Sprache, Zeitzone und Wochenformat'],
    organization: ['Organisation', 'Mitglieder, Rollen, Einladungen und Prüfung'],
    developer: ['Entwicklung', 'API-Dokumentation und Integrationszugänge'],
  },
  ar: {
    overview: ['نظرة عامة', 'سلامة الحساب والإجراءات المقترحة'],
    profile: ['الملف الشخصي', 'الهوية والمعلومات العامة'],
    security: ['تسجيل الدخول والأمان', 'المصادقة والاسترداد والأجهزة والجلسات'],
    privacy: ['الخصوصية والبيانات', 'الموافقات والتصدير والتصحيح والحذف'],
    notifications: ['الإشعارات', 'رسائل الأمان والمنتج والتسويق'],
    appearance: ['المظهر وإمكانية الوصول', 'السمة والتباين والحركة والكثافة'],
    'language-region': ['اللغة والمنطقة', 'اللغة والمنطقة الزمنية وتنسيق الأسبوع'],
    organization: ['المؤسسة', 'الأعضاء والأدوار والدعوات وسجل التدقيق'],
    developer: ['المطور', 'توثيق الواجهة البرمجية وبيانات التكامل'],
  },
};

const DETAIL_COPY = {
  en: {
    partialError: 'Some settings are temporarily unavailable. Existing values were not changed.',
    profileSaved: 'Profile saved.',
    preferencesSaved: 'Preferences saved.',
    settingsConflict: 'These settings changed elsewhere. Refresh before saving again.',
    exportQueued: 'Your data export was queued securely.',
    correctionQueued: 'Your correction request was queued securely.',
    deletionQueued: 'Your account deletion request was queued securely.',
    deactivationQueued: 'Your account deactivation request was queued securely.',
    email: 'Email',
    emailHint: 'Changing your email requires verification.',
    displayName: 'Display name',
    avatarUrl: 'Avatar URL',
    avatarHint: 'Use a public HTTPS image. Local and credential-bearing URLs are rejected.',
    bio: 'Bio',
    saveProfile: 'Save profile',
    theme: 'Theme',
    contrast: 'Contrast',
    motion: 'Motion',
    density: 'Density',
    useSystem: 'Use system',
    light: 'Light',
    dark: 'Dark',
    standard: 'Standard',
    highContrast: 'High contrast',
    fullMotion: 'Full motion',
    reducedMotion: 'Reduced motion',
    comfortable: 'Comfortable',
    compact: 'Compact',
    deliveryControls: 'Delivery controls',
    deliveryHelp:
      'Required security and transactional email cannot be disabled. Optional messages remain under your control.',
    requiredMessage: 'Required account message',
    optionalMessage: 'Optional message',
    immediately: 'Immediately',
    digest: 'Digest',
    off: 'Off',
    saveNotifications: 'Save notifications',
    notificationSaved: 'Notification preferences saved.',
    notificationDeliveryLabel: (eventFamily, channel) => `${eventFamily} ${channel} delivery`,
    notificationTerms: {
      security: 'Security',
      transactional: 'Transactional',
      product: 'Product',
      marketing: 'Marketing',
      email: 'Email',
      in_app: 'In-app',
    },
    exportData: 'Export your data',
    exportHelp:
      'Exports are encrypted, integrity checked, and require recent authentication to download.',
    requestExport: 'Request data export',
    correctData: 'Correct your data',
    correctHelp:
      'Submit only the fields that need correction. Requests are auditable and processed asynchronously.',
    correctName: 'Correct display name',
    correctBio: 'Correct bio',
    requestCorrection: 'Request correction',
    deactivate: 'Deactivate account',
    deactivateHelp:
      'Deactivation signs you out and suspends access without erasing your profile. A final organization owner must transfer ownership first. Type DEACTIVATE exactly.',
    deactivateConfirmation: 'Deactivation confirmation',
    requestDeactivation: 'Request deactivation',
    deleteData: 'Delete account data',
    deleteHelp:
      'This starts a destructive, auditable workflow after recent authentication. Type DELETE exactly to continue.',
    confirmation: 'Confirmation',
    requestDeletion: 'Request account deletion',
    recentRequests: 'Recent requests',
    membersRoles: 'Members and roles',
    membersHelp: 'Invite members, assign least-privilege roles, and review organization access.',
    openAdministration: 'Open organization administration',
    securityActivity: 'Recent security activity',
    noSecurityEvents: 'No recent security events are available.',
    accountEvent: 'Account event',
    apiDocs: 'API documentation',
    apiDocsHelp: 'Explore the generated API contract and integration schemas.',
    openApiDocs: 'Open API documentation',
    credentials: 'Integration credentials',
    credentialsHelp: 'Credentials are created once, shown once, scoped, and revocable.',
    manageCredentials: 'Manage credentials',
    saving: 'Saving…',
    actionFailed: 'The requested settings action could not be completed.',
  },
  de: {
    partialError:
      'Einige Einstellungen sind vorübergehend nicht verfügbar. Vorhandene Werte wurden nicht geändert.',
    profileSaved: 'Profil gespeichert.',
    preferencesSaved: 'Einstellungen gespeichert.',
    settingsConflict:
      'Diese Einstellungen wurden an anderer Stelle geändert. Aktualisieren Sie die Seite vor dem erneuten Speichern.',
    exportQueued: 'Ihr Datenexport wurde sicher in die Warteschlange gestellt.',
    correctionQueued: 'Ihre Korrekturanfrage wurde sicher in die Warteschlange gestellt.',
    deletionQueued: 'Ihre Anfrage zur Kontolöschung wurde sicher in die Warteschlange gestellt.',
    deactivationQueued: 'Ihre Anfrage zur Kontodeaktivierung wurde sicher vorgemerkt.',
    email: 'E-Mail',
    emailHint: 'Eine Änderung Ihrer E-Mail-Adresse muss bestätigt werden.',
    displayName: 'Anzeigename',
    avatarUrl: 'Avatar-URL',
    avatarHint:
      'Verwenden Sie ein öffentliches HTTPS-Bild. Lokale URLs und URLs mit Zugangsdaten werden abgelehnt.',
    bio: 'Biografie',
    saveProfile: 'Profil speichern',
    theme: 'Design',
    contrast: 'Kontrast',
    motion: 'Bewegung',
    density: 'Dichte',
    useSystem: 'Systemeinstellung verwenden',
    light: 'Hell',
    dark: 'Dunkel',
    standard: 'Standard',
    highContrast: 'Hoher Kontrast',
    fullMotion: 'Volle Bewegung',
    reducedMotion: 'Reduzierte Bewegung',
    comfortable: 'Komfortabel',
    compact: 'Kompakt',
    deliveryControls: 'Zustellung',
    deliveryHelp:
      'Erforderliche Sicherheits- und Transaktions-E-Mails können nicht deaktiviert werden. Optionale Nachrichten bleiben unter Ihrer Kontrolle.',
    requiredMessage: 'Erforderliche Kontonachricht',
    optionalMessage: 'Optionale Nachricht',
    immediately: 'Sofort',
    digest: 'Zusammenfassung',
    off: 'Aus',
    saveNotifications: 'Benachrichtigungen speichern',
    notificationSaved: 'Benachrichtigungseinstellungen gespeichert.',
    notificationDeliveryLabel: (eventFamily, channel) =>
      `Zustellung für ${eventFamily} über ${channel}`,
    notificationTerms: {
      security: 'Sicherheit',
      transactional: 'Transaktionen',
      product: 'Produkt',
      marketing: 'Marketing',
      email: 'E-Mail',
      in_app: 'In-App',
    },
    exportData: 'Daten exportieren',
    exportHelp:
      'Exporte werden verschlüsselt, auf Integrität geprüft und erfordern für den Download eine kürzliche Anmeldung.',
    requestExport: 'Datenexport anfordern',
    correctData: 'Daten korrigieren',
    correctHelp:
      'Übermitteln Sie nur zu korrigierende Felder. Anfragen werden protokolliert und asynchron verarbeitet.',
    correctName: 'Anzeigenamen korrigieren',
    correctBio: 'Biografie korrigieren',
    requestCorrection: 'Korrektur anfordern',
    deactivate: 'Konto deaktivieren',
    deactivateHelp:
      'Die Deaktivierung meldet Sie ab und sperrt den Zugriff, ohne Ihr Profil zu löschen. Der letzte Organisationsinhaber muss die Inhaberschaft zuerst übertragen. Geben Sie DEACTIVATE exakt ein.',
    deactivateConfirmation: 'Deaktivierung bestätigen',
    requestDeactivation: 'Deaktivierung anfordern',
    deleteData: 'Kontodaten löschen',
    deleteHelp:
      'Dies startet nach einer kürzlichen Anmeldung einen destruktiven, protokollierten Ablauf. Geben Sie DELETE exakt ein.',
    confirmation: 'Bestätigung',
    requestDeletion: 'Kontolöschung anfordern',
    recentRequests: 'Letzte Anfragen',
    membersRoles: 'Mitglieder und Rollen',
    membersHelp:
      'Laden Sie Mitglieder ein, vergeben Sie Rollen mit minimalen Rechten und prüfen Sie den Organisationszugriff.',
    openAdministration: 'Organisationsverwaltung öffnen',
    securityActivity: 'Letzte Sicherheitsaktivität',
    noSecurityEvents: 'Keine aktuellen Sicherheitsereignisse verfügbar.',
    accountEvent: 'Kontoereignis',
    apiDocs: 'API-Dokumentation',
    apiDocsHelp: 'Erkunden Sie den generierten API-Vertrag und die Integrationsschemata.',
    openApiDocs: 'API-Dokumentation öffnen',
    credentials: 'Integrationszugangsdaten',
    credentialsHelp:
      'Zugangsdaten werden einmal erstellt, einmal angezeigt, eingeschränkt und können widerrufen werden.',
    manageCredentials: 'Zugangsdaten verwalten',
    saving: 'Wird gespeichert…',
    actionFailed: 'Die angeforderte Einstellungsaktion konnte nicht abgeschlossen werden.',
  },
  ar: {
    partialError: 'بعض الإعدادات غير متاحة مؤقتًا. لم تتغير القيم الحالية.',
    profileSaved: 'تم حفظ الملف الشخصي.',
    preferencesSaved: 'تم حفظ التفضيلات.',
    settingsConflict: 'تغيرت هذه الإعدادات في مكان آخر. حدّث الصفحة قبل الحفظ مرة أخرى.',
    exportQueued: 'تمت إضافة تصدير بياناتك إلى قائمة الانتظار بأمان.',
    correctionQueued: 'تمت إضافة طلب التصحيح إلى قائمة الانتظار بأمان.',
    deletionQueued: 'تمت إضافة طلب حذف الحساب إلى قائمة الانتظار بأمان.',
    deactivationQueued: 'تمت إضافة طلب تعطيل الحساب إلى قائمة الانتظار بأمان.',
    email: 'البريد الإلكتروني',
    emailHint: 'يتطلب تغيير البريد الإلكتروني التحقق منه.',
    displayName: 'اسم العرض',
    avatarUrl: 'رابط الصورة الشخصية',
    avatarHint: 'استخدم صورة HTTPS عامة. تُرفض الروابط المحلية والروابط التي تتضمن بيانات اعتماد.',
    bio: 'نبذة',
    saveProfile: 'حفظ الملف الشخصي',
    theme: 'السمة',
    contrast: 'التباين',
    motion: 'الحركة',
    density: 'الكثافة',
    useSystem: 'استخدام إعداد النظام',
    light: 'فاتح',
    dark: 'داكن',
    standard: 'قياسي',
    highContrast: 'تباين عالٍ',
    fullMotion: 'حركة كاملة',
    reducedMotion: 'حركة مخفّضة',
    comfortable: 'مريح',
    compact: 'مضغوط',
    deliveryControls: 'خيارات التسليم',
    deliveryHelp:
      'لا يمكن تعطيل رسائل الأمان والمعاملات المطلوبة. تظل الرسائل الاختيارية تحت تحكمك.',
    requiredMessage: 'رسالة حساب مطلوبة',
    optionalMessage: 'رسالة اختيارية',
    immediately: 'فورًا',
    digest: 'ملخص',
    off: 'إيقاف',
    saveNotifications: 'حفظ الإشعارات',
    notificationSaved: 'تم حفظ تفضيلات الإشعارات.',
    notificationDeliveryLabel: (eventFamily, channel) => `تسليم ${eventFamily} عبر ${channel}`,
    notificationTerms: {
      security: 'الأمان',
      transactional: 'المعاملات',
      product: 'المنتج',
      marketing: 'التسويق',
      email: 'البريد الإلكتروني',
      in_app: 'داخل التطبيق',
    },
    exportData: 'تصدير بياناتك',
    exportHelp: 'تُشفّر عمليات التصدير ويُتحقق من سلامتها، ويتطلب تنزيلها مصادقة حديثة.',
    requestExport: 'طلب تصدير البيانات',
    correctData: 'تصحيح بياناتك',
    correctHelp: 'أرسل الحقول التي تحتاج إلى تصحيح فقط. تُسجّل الطلبات وتُعالج بشكل غير متزامن.',
    correctName: 'تصحيح اسم العرض',
    correctBio: 'تصحيح النبذة',
    requestCorrection: 'طلب التصحيح',
    deactivate: 'تعطيل الحساب',
    deactivateHelp:
      'يسجّلك التعطيل خروجًا ويوقف الوصول دون مسح ملفك. يجب على آخر مالك للمؤسسة نقل الملكية أولًا. اكتب DEACTIVATE تمامًا.',
    deactivateConfirmation: 'تأكيد التعطيل',
    requestDeactivation: 'طلب التعطيل',
    deleteData: 'حذف بيانات الحساب',
    deleteHelp: 'يبدأ هذا إجراءً تدميريًا مسجلًا بعد مصادقة حديثة. اكتب DELETE تمامًا للمتابعة.',
    confirmation: 'التأكيد',
    requestDeletion: 'طلب حذف الحساب',
    recentRequests: 'الطلبات الحديثة',
    membersRoles: 'الأعضاء والأدوار',
    membersHelp: 'ادعُ الأعضاء وحدد أدوارًا بأقل الصلاحيات وراجع الوصول إلى المؤسسة.',
    openAdministration: 'فتح إدارة المؤسسة',
    securityActivity: 'نشاط الأمان الحديث',
    noSecurityEvents: 'لا تتوفر أحداث أمان حديثة.',
    accountEvent: 'حدث الحساب',
    apiDocs: 'توثيق الواجهة البرمجية',
    apiDocsHelp: 'استكشف عقد الواجهة البرمجية ومخططات التكامل المُنشأة.',
    openApiDocs: 'فتح توثيق الواجهة البرمجية',
    credentials: 'بيانات اعتماد التكامل',
    credentialsHelp:
      'تُنشأ بيانات الاعتماد مرة واحدة وتُعرض مرة واحدة وتكون محدودة وقابلة للإلغاء.',
    manageCredentials: 'إدارة بيانات الاعتماد',
    saving: 'جارٍ الحفظ…',
    actionFailed: 'تعذر إكمال إجراء الإعدادات المطلوب.',
  },
};

const Field = ({ label, htmlFor, hint, children }) => (
  <div className="space-y-2">
    <label className="block text-sm font-semibold" htmlFor={htmlFor}>
      {label}
    </label>
    {children}
    {hint ? <p className="text-xs opacity-70">{hint}</p> : null}
  </div>
);

const Select = ({ id, value, onChange, children, ...props }) => (
  <select
    id={id}
    value={value}
    onChange={onChange}
    {...props}
    className="w-full rounded-xl border border-white/20 bg-black/30 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-violet-300"
  >
    {children}
  </select>
);

const SettingsCenter = () => {
  const { user, updateUser } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const active = location.pathname.replace(/^\/settings\/?/, '') || 'overview';
  const [query, setQuery] = useState('');
  const [categories, setCategories] = useState(FALLBACK_CATEGORIES);
  const [preferences, setPreferences] = useState(preferenceDefaults);
  const [profile, setProfile] = useState({
    email: user?.email || '',
    display_name: user?.display_name || '',
    avatar_url: user?.avatar_url || '',
    bio: user?.bio || '',
  });
  const [operations, setOperations] = useState([]);
  const [notifications, setNotifications] = useState(DEFAULT_NOTIFICATIONS);
  const [securityEvents, setSecurityEvents] = useState([]);
  const [correction, setCorrection] = useState({ display_name: '', bio: '' });
  const [deleteConfirmation, setDeleteConfirmation] = useState('');
  const [deactivateConfirmation, setDeactivateConfirmation] = useState('');
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeLocale, setActiveLocale] = useState(
    () => String(user?.locale || 'en').split('-')[0]
  );
  const requestedLocale = String(activeLocale || 'en').split('-')[0];
  const locale = Object.prototype.hasOwnProperty.call(SETTINGS_COPY, requestedLocale)
    ? requestedLocale
    : 'en';
  const copy = SETTINGS_COPY[locale];
  const detail = DETAIL_COPY[locale];
  const localizedCategories = useMemo(
    () =>
      categories.map((item) => {
        const localized = CATEGORY_COPY[locale]?.[item.id];
        return localized ? { ...item, label: localized[0], description: localized[1] } : item;
      }),
    [categories, locale]
  );

  useEffect(() => {
    const prior = { lang: document.documentElement.lang, dir: document.documentElement.dir };
    document.documentElement.lang = locale;
    document.documentElement.dir = locale === 'ar' ? 'rtl' : 'ltr';
    return () => {
      document.documentElement.lang = prior.lang;
      document.documentElement.dir = prior.dir;
    };
  }, [locale]);

  useEffect(() => {
    let current = true;
    Promise.allSettled([
      settingsAPI.capabilities(),
      settingsAPI.preferences(),
      settingsAPI.privacyOperations(),
      settingsAPI.notifications(),
      settingsAPI.securityEvents(),
    ]).then(
      ([capabilityResult, preferenceResult, privacyResult, notificationResult, securityResult]) => {
        if (!current) return;
        if (
          capabilityResult.status === 'fulfilled' &&
          Array.isArray(capabilityResult.value?.categories)
        ) {
          const enabled = new Set(capabilityResult.value.categories.map((item) => item.id));
          setCategories(FALLBACK_CATEGORIES.filter((item) => enabled.has(item.id)));
        }
        if (preferenceResult.status === 'fulfilled') {
          const nextPreferences = {
            ...preferenceDefaults,
            ...preferenceResult.value,
            locale: preferenceResult.value?.locale || user?.locale || preferenceDefaults.locale,
          };
          setPreferences(nextPreferences);
          setActiveLocale(String(nextPreferences.locale || 'en').split('-')[0]);
        }
        if (privacyResult.status === 'fulfilled') {
          setOperations(privacyResult.value?.operations || []);
        }
        if (
          notificationResult.status === 'fulfilled' &&
          notificationResult.value?.preferences?.length
        ) {
          setNotifications(notificationResult.value.preferences);
        }
        if (securityResult.status === 'fulfilled')
          setSecurityEvents(securityResult.value?.events || []);
        if ([capabilityResult, preferenceResult].some((result) => result.status === 'rejected')) {
          const responseLocale = String(
            preferenceResult.value?.locale || user?.locale || 'en'
          ).split('-')[0];
          setError((DETAIL_COPY[responseLocale] || DETAIL_COPY.en).partialError);
        }
        setLoading(false);
      }
    );
    return () => {
      current = false;
    };
  }, [user?.locale]);

  useEffect(() => {
    if (!loading && !localizedCategories.some((item) => item.id === active))
      navigate('/settings', { replace: true });
  }, [active, localizedCategories, loading, navigate]);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return localizedCategories;
    return localizedCategories.filter((item) =>
      `${item.label} ${item.description} ${item.id} ${item.synonyms}`.toLowerCase().includes(needle)
    );
  }, [localizedCategories, query]);

  const saveProfile = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    setStatus('');
    try {
      const response = await apiClient.patch('/users/me', profile);
      updateUser(response.data);
      setStatus(detail.profileSaved);
    } catch (reason) {
      setError(normalizeApiError(reason, { fallbackMessage: detail.actionFailed }).message);
    } finally {
      setSaving(false);
    }
  };

  const savePreferences = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    setStatus('');
    try {
      const next = await settingsAPI.savePreferences({
        expected_version: preferences.version,
        theme: preferences.theme,
        contrast: preferences.contrast,
        motion: preferences.motion,
        density: preferences.density,
        locale: preferences.locale,
        timezone: preferences.timezone,
        week_start: preferences.week_start,
      });
      setPreferences({ ...preferenceDefaults, ...next });
      setActiveLocale(String(next.locale || preferences.locale || 'en').split('-')[0]);
      updateUser({ ...user, locale: next.locale || preferences.locale || 'en' });
      setStatus(detail.preferencesSaved);
    } catch (reason) {
      if (reason?.status === 409 || reason?.code === 'settings_version_conflict') {
        setError(detail.settingsConflict);
      } else setError(reason.message || detail.actionFailed);
    } finally {
      setSaving(false);
    }
  };

  const requestExport = async () => {
    setSaving(true);
    setError('');
    setStatus('');
    try {
      await settingsAPI.requestExport();
      setStatus(detail.exportQueued);
    } catch (reason) {
      setError(reason.message || detail.actionFailed);
    } finally {
      setSaving(false);
    }
  };

  const saveNotifications = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    setStatus('');
    try {
      const result = await settingsAPI.saveNotifications(
        notifications.map(({ mandatory: _mandatory, ...item }) => item)
      );
      setNotifications(result.preferences);
      setStatus(detail.notificationSaved);
    } catch (reason) {
      setError(reason.message || detail.actionFailed);
    } finally {
      setSaving(false);
    }
  };

  const requestCorrection = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    setStatus('');
    const fields = Object.fromEntries(
      Object.entries(correction).filter(([, value]) => value.trim())
    );
    try {
      await settingsAPI.requestCorrection(fields);
      setCorrection({ display_name: '', bio: '' });
      setStatus(detail.correctionQueued);
    } catch (reason) {
      setError(reason.message || detail.actionFailed);
    } finally {
      setSaving(false);
    }
  };

  const requestDeletion = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    setStatus('');
    try {
      await settingsAPI.requestDeletion(deleteConfirmation);
      setDeleteConfirmation('');
      setStatus(detail.deletionQueued);
    } catch (reason) {
      setError(reason.message || detail.actionFailed);
    } finally {
      setSaving(false);
    }
  };

  const requestDeactivation = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    setStatus('');
    try {
      await settingsAPI.requestDeactivation(deactivateConfirmation);
      setDeactivateConfirmation('');
      setStatus(detail.deactivationQueued);
    } catch (reason) {
      setError(reason.message || detail.actionFailed);
    } finally {
      setSaving(false);
    }
  };

  const renderOverview = () => (
    <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,22rem),1fr))] gap-4">
      {filtered
        .filter((item) => item.id !== 'overview')
        .map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.id}
              to={item.path}
              className="group min-w-0 overflow-hidden rounded-2xl focus:outline-none focus:ring-2 focus:ring-violet-300"
            >
              <GlassCard>
                <div className="flex min-h-32 items-start gap-4 p-5">
                  <span className="rounded-xl bg-violet-400/15 p-3">
                    <Icon className="h-5 w-5" aria-hidden="true" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <strong className="block">{item.label}</strong>
                    <span className="mt-2 block text-sm opacity-70">{item.description}</span>
                  </span>
                  <ChevronRight
                    className="mt-1 h-4 w-4 opacity-50 transition-transform group-hover:translate-x-1"
                    aria-hidden="true"
                  />
                </div>
              </GlassCard>
            </Link>
          );
        })}
    </div>
  );

  const renderProfile = () => (
    <GlassCard>
      <form onSubmit={saveProfile} className="space-y-5 p-6">
        <Field label={detail.email} htmlFor="email" hint={detail.emailHint}>
          <GlassInput
            id="email"
            type="email"
            value={profile.email}
            onChange={(event) => setProfile({ ...profile, email: event.target.value })}
          />
        </Field>
        <Field label={detail.displayName} htmlFor="display-name">
          <GlassInput
            id="display-name"
            value={profile.display_name}
            onChange={(event) => setProfile({ ...profile, display_name: event.target.value })}
          />
        </Field>
        <Field label={detail.avatarUrl} htmlFor="avatar-url" hint={detail.avatarHint}>
          <GlassInput
            id="avatar-url"
            type="url"
            value={profile.avatar_url}
            onChange={(event) => setProfile({ ...profile, avatar_url: event.target.value })}
          />
        </Field>
        <Field label={detail.bio} htmlFor="bio">
          <textarea
            id="bio"
            rows="5"
            value={profile.bio}
            onChange={(event) => setProfile({ ...profile, bio: event.target.value })}
            className="w-full rounded-xl border border-white/20 bg-black/30 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-violet-300"
          />
        </Field>
        <GlassButton type="submit" disabled={saving}>
          {saving ? detail.saving : detail.saveProfile}
        </GlassButton>
      </form>
    </GlassCard>
  );

  const renderPreferences = (language = false) => (
    <GlassCard>
      <form onSubmit={savePreferences} className="grid gap-5 p-6 sm:grid-cols-2">
        {language ? (
          <>
            <Field label={copy.language} htmlFor="locale">
              <Select
                id="locale"
                value={preferences.locale}
                onChange={(event) => setPreferences({ ...preferences, locale: event.target.value })}
              >
                <option value="en">English</option>
                <option value="de">Deutsch</option>
                <option value="ar">العربية</option>
              </Select>
            </Field>
            <Field label={copy.timezone} htmlFor="timezone">
              <GlassInput
                id="timezone"
                value={preferences.timezone}
                onChange={(event) =>
                  setPreferences({ ...preferences, timezone: event.target.value })
                }
              />
            </Field>
            <Field label={copy.weekStart} htmlFor="week-start">
              <Select
                id="week-start"
                value={preferences.week_start}
                onChange={(event) =>
                  setPreferences({ ...preferences, week_start: event.target.value })
                }
              >
                <option value="system">{copy.systemDefault}</option>
                <option value="monday">{copy.monday}</option>
                <option value="sunday">{copy.sunday}</option>
                <option value="saturday">{copy.saturday}</option>
              </Select>
            </Field>
          </>
        ) : (
          <>
            <Field label={detail.theme} htmlFor="theme">
              <Select
                id="theme"
                value={preferences.theme}
                onChange={(event) => setPreferences({ ...preferences, theme: event.target.value })}
              >
                <option value="system">{detail.useSystem}</option>
                <option value="light">{detail.light}</option>
                <option value="dark">{detail.dark}</option>
              </Select>
            </Field>
            <Field label={detail.contrast} htmlFor="contrast">
              <Select
                id="contrast"
                value={preferences.contrast}
                onChange={(event) =>
                  setPreferences({ ...preferences, contrast: event.target.value })
                }
              >
                <option value="system">{detail.useSystem}</option>
                <option value="standard">{detail.standard}</option>
                <option value="high">{detail.highContrast}</option>
              </Select>
            </Field>
            <Field label={detail.motion} htmlFor="motion">
              <Select
                id="motion"
                value={preferences.motion}
                onChange={(event) => setPreferences({ ...preferences, motion: event.target.value })}
              >
                <option value="system">{detail.useSystem}</option>
                <option value="full">{detail.fullMotion}</option>
                <option value="reduced">{detail.reducedMotion}</option>
              </Select>
            </Field>
            <Field label={detail.density} htmlFor="density">
              <Select
                id="density"
                value={preferences.density}
                onChange={(event) =>
                  setPreferences({ ...preferences, density: event.target.value })
                }
              >
                <option value="comfortable">{detail.comfortable}</option>
                <option value="compact">{detail.compact}</option>
              </Select>
            </Field>
          </>
        )}
        <div className="sm:col-span-2">
          <GlassButton type="submit" disabled={saving}>
            {saving ? copy.saving : copy.savePreferences}
          </GlassButton>
        </div>
      </form>
    </GlassCard>
  );

  const renderNotifications = () => (
    <GlassCard>
      <form onSubmit={saveNotifications} className="space-y-5 p-6">
        <div>
          <h2 className="font-semibold">{detail.deliveryControls}</h2>
          <p className="mt-2 text-sm opacity-75">{detail.deliveryHelp}</p>
        </div>
        <div className="divide-y divide-white/10 rounded-xl border border-white/15">
          {notifications.map((item, index) => (
            <div
              className="grid gap-3 p-4 sm:grid-cols-[1fr_12rem] sm:items-center"
              key={`${item.event_family}-${item.channel}`}
            >
              <div>
                <p className="font-medium capitalize">
                  {detail.notificationTerms[item.event_family] || item.event_family} ·{' '}
                  {detail.notificationTerms[item.channel] || item.channel.replace('_', ' ')}
                </p>
                <p className="text-xs opacity-70">
                  {item.mandatory ? detail.requiredMessage : detail.optionalMessage}
                </p>
              </div>
              <Select
                id={`notification-${item.event_family}-${item.channel}`}
                aria-label={detail.notificationDeliveryLabel(
                  detail.notificationTerms[item.event_family] || item.event_family,
                  detail.notificationTerms[item.channel] || item.channel.replace('_', ' ')
                )}
                value={item.delivery}
                onChange={(event) =>
                  setNotifications(
                    notifications.map((choice, choiceIndex) =>
                      choiceIndex === index ? { ...choice, delivery: event.target.value } : choice
                    )
                  )
                }
              >
                <option value="immediate">{detail.immediately}</option>
                <option value="digest">{detail.digest}</option>
                {!item.mandatory ? <option value="disabled">{detail.off}</option> : null}
              </Select>
            </div>
          ))}
        </div>
        <GlassButton type="submit" disabled={saving}>
          {saving ? detail.saving : detail.saveNotifications}
        </GlassButton>
      </form>
    </GlassCard>
  );

  const renderPrivacy = () => (
    <div className="space-y-4">
      <GlassCard>
        <div className="p-6">
          <h2 className="font-semibold">{detail.exportData}</h2>
          <p className="mt-2 text-sm opacity-75">{detail.exportHelp}</p>
          <GlassButton className="mt-4" onClick={requestExport} disabled={saving}>
            {detail.requestExport}
          </GlassButton>
        </div>
      </GlassCard>
      <GlassCard>
        <form onSubmit={requestCorrection} className="space-y-4 p-6">
          <div>
            <h2 className="font-semibold">{detail.correctData}</h2>
            <p className="mt-2 text-sm opacity-75">{detail.correctHelp}</p>
          </div>
          <Field label={detail.correctName} htmlFor="correct-display-name">
            <GlassInput
              id="correct-display-name"
              value={correction.display_name}
              onChange={(event) =>
                setCorrection({ ...correction, display_name: event.target.value })
              }
            />
          </Field>
          <Field label={detail.correctBio} htmlFor="correct-bio">
            <textarea
              id="correct-bio"
              rows="3"
              value={correction.bio}
              onChange={(event) => setCorrection({ ...correction, bio: event.target.value })}
              className="w-full rounded-xl border border-white/20 bg-black/30 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-violet-300"
            />
          </Field>
          <GlassButton
            type="submit"
            disabled={saving || !Object.values(correction).some((value) => value.trim())}
          >
            {detail.requestCorrection}
          </GlassButton>
        </form>
      </GlassCard>
      <GlassCard>
        <form onSubmit={requestDeactivation} className="space-y-4 border border-amber-400/20 p-6">
          <div>
            <h2 className="font-semibold text-amber-100">{detail.deactivate}</h2>
            <p className="mt-2 text-sm opacity-75">{detail.deactivateHelp}</p>
          </div>
          <Field label={detail.deactivateConfirmation} htmlFor="deactivate-confirmation">
            <GlassInput
              id="deactivate-confirmation"
              value={deactivateConfirmation}
              onChange={(event) => setDeactivateConfirmation(event.target.value)}
              autoComplete="off"
            />
          </Field>
          <GlassButton type="submit" disabled={saving || deactivateConfirmation !== 'DEACTIVATE'}>
            {detail.requestDeactivation}
          </GlassButton>
        </form>
      </GlassCard>
      <GlassCard>
        <form onSubmit={requestDeletion} className="space-y-4 border border-red-400/20 p-6">
          <div>
            <h2 className="font-semibold text-red-200">{detail.deleteData}</h2>
            <p className="mt-2 text-sm opacity-75">{detail.deleteHelp}</p>
          </div>
          <Field label={detail.confirmation} htmlFor="delete-confirmation">
            <GlassInput
              id="delete-confirmation"
              value={deleteConfirmation}
              onChange={(event) => setDeleteConfirmation(event.target.value)}
              autoComplete="off"
            />
          </Field>
          <GlassButton
            type="submit"
            variant="danger"
            disabled={saving || deleteConfirmation !== 'DELETE'}
          >
            {detail.requestDeletion}
          </GlassButton>
        </form>
      </GlassCard>
      {operations.length ? (
        <GlassCard>
          <div className="p-6">
            <h2 className="font-semibold">{detail.recentRequests}</h2>
            <ul className="mt-3 space-y-2 text-sm">
              {operations.map((item) => (
                <li key={item.id} className="flex justify-between gap-3">
                  <span className="capitalize">{item.kind}</span>
                  <span>{item.status}</span>
                </li>
              ))}
            </ul>
          </div>
        </GlassCard>
      ) : null}
    </div>
  );

  const renderOrganization = () => (
    <div className="grid gap-4 sm:grid-cols-2">
      <GlassCard>
        <div className="p-6">
          <h2 className="font-semibold">{detail.membersRoles}</h2>
          <p className="mt-2 text-sm opacity-75">{detail.membersHelp}</p>
          <Link
            className="mt-4 inline-flex min-h-11 items-center font-semibold text-violet-200"
            to="/admin"
          >
            {detail.openAdministration}
          </Link>
        </div>
      </GlassCard>
      <GlassCard>
        <div className="p-6">
          <h2 className="font-semibold">{detail.securityActivity}</h2>
          {securityEvents.length ? (
            <ul className="mt-3 space-y-2 text-sm">
              {securityEvents.slice(0, 5).map((event, index) => (
                <li key={event.id || index}>{event.action || detail.accountEvent}</li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm opacity-75">{detail.noSecurityEvents}</p>
          )}
        </div>
      </GlassCard>
    </div>
  );

  const renderDeveloper = () => (
    <div className="grid gap-4 sm:grid-cols-2">
      <GlassCard>
        <div className="p-6">
          <h2 className="font-semibold">{detail.apiDocs}</h2>
          <p className="mt-2 text-sm opacity-75">{detail.apiDocsHelp}</p>
          <a
            className="mt-4 inline-flex min-h-11 items-center font-semibold text-violet-200"
            href="/docs"
          >
            {detail.openApiDocs}
          </a>
        </div>
      </GlassCard>
      <GlassCard>
        <div className="p-6">
          <h2 className="font-semibold">{detail.credentials}</h2>
          <p className="mt-2 text-sm opacity-75">{detail.credentialsHelp}</p>
          <Link
            className="mt-4 inline-flex min-h-11 items-center font-semibold text-violet-200"
            to="/admin"
          >
            {detail.manageCredentials}
          </Link>
        </div>
      </GlassCard>
    </div>
  );

  const renderSimple = () => {
    if (active === 'security') return <AccountCenter user={user} embedded locale={locale} />;
    if (active === 'privacy') return renderPrivacy();
    if (active === 'notifications') return renderNotifications();
    if (active === 'organization') return renderOrganization();
    if (active === 'developer') return renderDeveloper();
    return renderOverview();
  };

  const current = localizedCategories.find((item) => item.id === active) || localizedCategories[0];
  return (
    <AppShell
      headerTitle={copy.appShell}
      headerIsPageHeading={false}
      footerLabel={copy.privateWorkspace}
      menuLabel={copy.menu}
      themeLabel={copy.themeToggle}
      sidebarLabel={copy.sidebar}
      sidebarItems={copy.sidebarItems}
    >
      <div
        className="mx-auto max-w-7xl space-y-6 px-4 py-8"
        lang={locale}
        dir={locale === 'ar' ? 'rtl' : 'ltr'}
      >
        <Navigation />
        <nav aria-label={copy.breadcrumb} className="flex items-center gap-2 text-sm opacity-75">
          <Link className="min-h-11 py-3 hover:underline" to="/settings">
            {copy.settings}
          </Link>
          {active !== 'overview' ? (
            <>
              <span aria-hidden="true">/</span>
              <span aria-current="page">{current?.label}</span>
            </>
          ) : null}
        </nav>
        <header>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-violet-300">
            {copy.controlCenter}
          </p>
          <h1 className="mt-2 text-3xl font-semibold">{current?.label || copy.settings}</h1>
          <p className="mt-2 max-w-2xl text-sm opacity-75">{current?.description}</p>
        </header>
        {status ? (
          <div
            role="status"
            className="rounded-xl border border-emerald-400/30 bg-emerald-400/10 p-4 text-sm"
          >
            {status}
          </div>
        ) : null}
        {error ? (
          <div
            role="alert"
            className="rounded-xl border border-amber-400/30 bg-amber-400/10 p-4 text-sm"
          >
            {error}
          </div>
        ) : null}
        <div className="grid gap-6 lg:grid-cols-[17rem_minmax(0,1fr)]">
          <aside className="space-y-4 lg:sticky lg:top-28 lg:self-start">
            <Field label={copy.search} htmlFor="settings-search">
              <div className="relative">
                <Search
                  className="pointer-events-none absolute start-3 top-3.5 h-4 w-4 opacity-60"
                  aria-hidden="true"
                />
                <input
                  id="settings-search"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  className="min-h-11 w-full rounded-xl border border-white/20 bg-black/30 ps-10 pe-3 focus:outline-none focus:ring-2 focus:ring-violet-300"
                />
              </div>
            </Field>
            <nav
              aria-label={copy.categories}
              className="max-h-[calc(100vh-15rem)] space-y-1 overflow-y-auto rounded-2xl border border-white/15 bg-black/20 p-2"
            >
              {filtered.map((item) => {
                const Icon = item.icon;
                return (
                  <Link
                    key={item.id}
                    to={item.path}
                    aria-current={item.id === active ? 'page' : undefined}
                    className={`flex min-h-12 items-center gap-3 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-300 ${item.id === active ? 'bg-violet-400/20' : 'hover:bg-white/10'}`}
                  >
                    <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
              {!filtered.length ? <p className="p-3 text-sm opacity-70">{copy.noResults}</p> : null}
            </nav>
          </aside>
          <section
            id="settings-detail"
            aria-label={`${current?.label || copy.settings} ${copy.details}`}
            aria-busy={loading}
          >
            {loading ? (
              <GlassCard>
                <div className="p-8 text-sm">{copy.loading}</div>
              </GlassCard>
            ) : active === 'overview' ? (
              renderOverview()
            ) : active === 'profile' ? (
              renderProfile()
            ) : active === 'appearance' ? (
              renderPreferences(false)
            ) : active === 'language-region' ? (
              renderPreferences(true)
            ) : (
              renderSimple()
            )}
          </section>
        </div>
      </div>
    </AppShell>
  );
};

export default SettingsCenter;
