import GlassCard from './glass/GlassCard';
import GlassButton from './glass/GlassButton';

export const workspacePolicyCopy = {
  en: {
    review: 'Publishing review',
    visibility: 'Workspace content visibility',
    site: 'Site',
    organization: 'Organization',
    unmapped: 'No organization mapped',
    provenance: 'Source',
    version: 'Version',
    migrated: 'Migrated compatibility policy',
    explicit: 'Saved shared policy',
    default: 'Conservative default',
    required: 'Review required',
    optional: 'Review not required',
    members: 'Active site members only',
    public: 'Public eligibility allowed',
    effective: 'Effective saved value',
    readOnly: 'Only active owners and administrators can change this policy.',
    restriction:
      'Policy changes are unavailable because storage transport assurance is unverified. Ask the site operator to verify the private asset transport.',
    unavailable: 'Workspace policy is unavailable. No permissive default has been assumed.',
    reload: 'Reload workspace policy',
    reviewHelp:
      'When enabled, review is required for new or edited publications. Existing published revisions stay unchanged until edited. Scheduled records may be blocked until valid independent approval exists.',
    visibilityHelp:
      'This applies to workspace-managed content, not every website or static page. Public eligibility never publishes drafts or exposes private assets; existing permissions still apply. Previously downloaded copies cannot be recalled.',
    policyChange:
      'A policy change can invalidate pending approvals. Reviewers may need to approve the current revision again.',
    save: 'Save policy',
    cancel: 'Cancel',
    confirm: 'Confirm policy change',
    keep: 'Keep editing',
    discard: 'Discard policy drafts and reload',
    saved: 'Workspace policy saved.',
    uncertain:
      'The policy save could not be confirmed. Drafts are preserved. Discard and reload before trying again; the server may have saved the change.',
  },
  de: {
    review: 'Veröffentlichungsprüfung',
    visibility: 'Sichtbarkeit von Arbeitsbereichsinhalten',
    site: 'Website',
    organization: 'Organisation',
    unmapped: 'Keine Organisation zugeordnet',
    provenance: 'Quelle',
    version: 'Version',
    migrated: 'Migrierte Kompatibilitätsrichtlinie',
    explicit: 'Gespeicherte gemeinsame Richtlinie',
    default: 'Vorsichtige Standardeinstellung',
    required: 'Prüfung erforderlich',
    optional: 'Keine Prüfung erforderlich',
    members: 'Nur aktive Website-Mitglieder',
    public: 'Öffentliche Freigabe zulässig',
    effective: 'Wirksamer gespeicherter Wert',
    readOnly: 'Nur aktive Eigentümer und Administratoren können diese Richtlinie ändern.',
    restriction:
      'Änderungen sind ohne geprüften Speichertransport nicht verfügbar. Bitten Sie den Betreiber, den privaten Dateitransport zu prüfen.',
    unavailable:
      'Die Arbeitsbereichsrichtlinie ist nicht verfügbar. Es wird keine freizügige Standardeinstellung angenommen.',
    reload: 'Arbeitsbereichsrichtlinie neu laden',
    reviewHelp:
      'Wenn aktiviert, erfordern neue oder bearbeitete Veröffentlichungen eine Prüfung. Bestehende Veröffentlichungen bleiben bis zur Bearbeitung unverändert. Geplante Inhalte können bis zur gültigen unabhängigen Genehmigung blockiert sein.',
    visibilityHelp:
      'Dies betrifft Arbeitsbereichsinhalte, nicht alle Website- oder statischen Seiten. Öffentliche Zulässigkeit veröffentlicht keine Entwürfe und gibt keine privaten Dateien frei. Bestehende Berechtigungen gelten weiterhin. Bereits heruntergeladene Kopien können nicht zurückgerufen werden.',
    policyChange:
      'Eine Richtlinienänderung kann ausstehende Genehmigungen ungültig machen. Die aktuelle Version muss möglicherweise erneut geprüft werden.',
    save: 'Richtlinie speichern',
    cancel: 'Abbrechen',
    confirm: 'Richtlinienänderung bestätigen',
    keep: 'Weiter bearbeiten',
    discard: 'Richtlinienentwürfe verwerfen und neu laden',
    saved: 'Arbeitsbereichsrichtlinie gespeichert.',
    uncertain:
      'Das Speichern konnte nicht bestätigt werden. Entwürfe bleiben erhalten. Verwerfen und laden Sie vor einem erneuten Versuch neu; die Änderung wurde möglicherweise gespeichert.',
  },
  ar: {
    review: 'مراجعة النشر',
    visibility: 'إمكانية رؤية محتوى مساحة العمل',
    site: 'الموقع',
    organization: 'المؤسسة',
    unmapped: 'لا توجد مؤسسة مرتبطة',
    provenance: 'المصدر',
    version: 'الإصدار',
    migrated: 'سياسة توافق مُرحّلة',
    explicit: 'سياسة مشتركة محفوظة',
    default: 'إعداد افتراضي احترازي',
    required: 'المراجعة مطلوبة',
    optional: 'المراجعة غير مطلوبة',
    members: 'أعضاء الموقع النشطون فقط',
    public: 'السماح بأهلية النشر العام',
    effective: 'القيمة المحفوظة الفعلية',
    readOnly: 'يمكن للمالكين والمسؤولين النشطين فقط تغيير هذه السياسة.',
    restriction:
      'التغييرات غير متاحة لأن ضمان نقل التخزين غير مؤكد. اطلب من مشغّل الموقع التحقق من نقل الملفات الخاصة.',
    unavailable: 'سياسة مساحة العمل غير متاحة. لم يُفترض إعداد افتراضي يسمح بالوصول.',
    reload: 'إعادة تحميل سياسة مساحة العمل',
    reviewHelp:
      'عند تفعيل هذا الخيار، تتطلب المنشورات الجديدة أو المعدلة مراجعة. تبقى المنشورات الحالية دون تغيير حتى تعديلها. قد يتوقف النشر المجدول حتى تتوفر موافقة مستقلة صالحة.',
    visibilityHelp:
      'ينطبق هذا على محتوى مساحة العمل، وليس كل صفحات الموقع أو الصفحات الثابتة. السماح بالأهلية العامة لا ينشر المسودات ولا يكشف الملفات الخاصة. تبقى الأذونات الحالية سارية. لا يمكن استرجاع النسخ التي تم تنزيلها سابقًا.',
    policyChange:
      'قد يؤدي تغيير السياسة إلى إبطال الموافقات المعلقة. قد يلزم اعتماد الإصدار الحالي مرة أخرى.',
    save: 'حفظ السياسة',
    cancel: 'إلغاء',
    confirm: 'تأكيد تغيير السياسة',
    keep: 'متابعة التحرير',
    discard: 'تجاهل مسودات السياسة وإعادة التحميل',
    saved: 'تم حفظ سياسة مساحة العمل.',
    uncertain:
      'تعذر تأكيد الحفظ. تم الاحتفاظ بالمسودات. تجاهلها وأعد التحميل قبل المحاولة مجددًا؛ ربما حُفظ التغيير.',
  },
};

export default function WorkspacePolicyCard({
  field,
  policy,
  draft,
  unavailable,
  busy,
  conflict,
  confirmation,
  locale,
  onChange,
  onSave,
  onConfirm,
  onKeep,
  onCancel,
  onReload,
}) {
  const copy = workspacePolicyCopy[locale] || workspacePolicyCopy.en;
  if (unavailable || !policy)
    return (
      <GlassCard>
        <div className="space-y-3 p-6">
          <p role="alert">{copy.unavailable}</p>
          <GlassButton disabled={busy} onClick={onReload}>
            {copy.reload}
          </GlassButton>
        </div>
      </GlassCard>
    );
  const review = field === 'require_review';
  const id = review ? 'workspace-publishing-review' : 'workspace-content-visibility';
  const label = review ? copy.review : copy.visibility;
  const locked = !policy.permissions.write || policy.restrictions.length > 0;
  const changed = draft[field] !== policy[field];
  const displayValue = review
    ? policy.require_review
      ? copy.required
      : copy.optional
    : policy.public_access === 'members_only'
      ? copy.members
      : copy.public;
  return (
    <GlassCard>
      <form
        className="space-y-4 p-6"
        onSubmit={(event) => {
          event.preventDefault();
          onSave(field);
        }}
      >
        <h2 className="font-semibold">{label}</h2>
        <p className="text-sm">
          {copy.site}: {policy.scope.site_id} · {copy.organization}:{' '}
          {policy.scope.organization_id || copy.unmapped}
        </p>
        <p className="text-xs opacity-75">
          {copy.provenance}: {copy[policy.provenance]} · {copy.version}: {policy.version}
        </p>
        <p className="text-sm">
          {copy.effective}: {displayValue}
        </p>
        <p className="text-sm opacity-75">{review ? copy.reviewHelp : copy.visibilityHelp}</p>
        <p className="text-sm opacity-75">{copy.policyChange}</p>
        {locked && (
          <p className="text-sm">{policy.restrictions.length ? copy.restriction : copy.readOnly}</p>
        )}
        <label className="block space-y-2 text-sm font-semibold" htmlFor={id}>
          <span>{label}</span>
          <select
            id={id}
            disabled={busy || locked || conflict}
            value={review ? (draft.require_review ? 'required' : 'optional') : draft.public_access}
            className="w-full rounded-xl border border-white/20 bg-black/30 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-violet-300"
            onChange={(event) =>
              onChange(field, review ? event.target.value === 'required' : event.target.value)
            }
          >
            {review ? (
              <>
                <option value="required">{copy.required}</option>
                <option value="optional">{copy.optional}</option>
              </>
            ) : (
              <>
                <option value="members_only">{copy.members}</option>
                <option value="public_allowed">{copy.public}</option>
              </>
            )}
          </select>
        </label>
        <div className="flex flex-wrap gap-3">
          <GlassButton type="submit" disabled={busy || locked || conflict || !changed}>
            {copy.save}
          </GlassButton>
          {!conflict && (
            <GlassButton
              disabled={busy || !changed}
              variant="secondary"
              onClick={() => onCancel(field)}
            >
              {copy.cancel}
            </GlassButton>
          )}
          {conflict && (
            <GlassButton disabled={busy} variant="secondary" onClick={onReload}>
              {copy.discard}
            </GlassButton>
          )}
        </div>
        {confirmation === field && !conflict && (
          <div
            role="alertdialog"
            aria-label={copy.confirm}
            className="space-y-3 rounded-xl border border-amber-300/30 p-4"
          >
            <p>{review ? copy.reviewHelp : copy.visibilityHelp}</p>
            <p>{copy.policyChange}</p>
            <div className="flex flex-wrap gap-3">
              <GlassButton disabled={busy || locked} onClick={() => onConfirm(field)}>
                {copy.confirm}
              </GlassButton>
              <GlassButton disabled={busy} variant="secondary" onClick={onKeep}>
                {copy.keep}
              </GlassButton>
            </div>
          </div>
        )}
      </form>
    </GlassCard>
  );
}
