export const workspaceReviewCopy = {
  en: {
    approve: 'Approve review',
    adopt: 'Adopt current snapshot',
    review: 'Review',
    pendingOptional: 'Workflow review stage — independent approval is not required',
    unknownOptional: 'Authorship unknown — independent approval is not required',
    policy: 'Policy version',
    authorship_unknown: 'Authorship unknown',
    approved: 'Approved',
    pending: 'Pending independent approval',
    not_requested: 'Not requested',
    unavailable: 'Review information unavailable',
    required:
      'New or edited publication requires valid independent approval. Existing published revisions remain unchanged.',
    optional: 'Review is not required by the current policy.',
    adapter:
      'Review notices use a local test adapter only: durable test receipts, not live email delivery. Policy or content changes may invalidate approval.',
    adoption:
      'I acknowledge the full snapshot as my authored content. This creates a fresh draft and never publishes it.',
    approval:
      'Approval must be independent of the authors of this revision and does not itself publish.',
    uncertain:
      'The change could not be confirmed or the record changed elsewhere. Your draft is retained. Reload before another write; the server may have completed the change.',
    reload: 'Discard draft and reload record',
    noReviewer:
      'No independent reviewer is currently eligible. Ask an organization owner or administrator to add or restore an active owner/admin who did not author this revision.',
    recoverPending:
      'This request remains pending. A newly eligible independent reviewer can approve it. To request another local-test notice, return it to draft and submit it for review again.',
    recoverDraft:
      'After an independent reviewer is available, submit the record for review. This does not grant permissions or send live email.',
    administration: 'Open organization administration',
    finishEditing: 'Finish or discard record edits before opening organization administration.',
  },
  de: {
    approve: 'Prüfung genehmigen',
    adopt: 'Aktuellen Stand übernehmen',
    review: 'Prüfung',
    pendingOptional: 'Prüfphase im Arbeitsablauf — keine unabhängige Genehmigung erforderlich',
    unknownOptional: 'Urheberschaft unbekannt — keine unabhängige Genehmigung erforderlich',
    policy: 'Richtlinienversion',
    authorship_unknown: 'Urheberschaft unbekannt',
    approved: 'Genehmigt',
    pending: 'Unabhängige Genehmigung ausstehend',
    not_requested: 'Nicht angefordert',
    unavailable: 'Prüfinformationen nicht verfügbar',
    required:
      'Neue oder bearbeitete Veröffentlichungen benötigen eine gültige unabhängige Genehmigung. Bestehende Veröffentlichungen bleiben unverändert.',
    optional: 'Die aktuelle Richtlinie erfordert keine Prüfung.',
    adapter:
      'Prüfhinweise verwenden nur einen lokalen Testadapter: dauerhafte Testbelege, keine Live-E-Mail. Änderungen an Richtlinie oder Inhalt können die Genehmigung ungültig machen.',
    adoption:
      'Ich bestätige den vollständigen Stand als meinen verfassten Inhalt. Dies erstellt einen neuen Entwurf und veröffentlicht ihn niemals.',
    approval:
      'Die Genehmigung muss unabhängig von den Autoren dieser Version erfolgen und veröffentlicht selbst nichts.',
    uncertain:
      'Die Änderung konnte nicht bestätigt werden oder der Inhalt wurde anderweitig geändert. Der Entwurf bleibt erhalten. Vor erneutem Schreiben neu laden; die Änderung könnte bereits gespeichert sein.',
    reload: 'Entwurf verwerfen und Inhalt neu laden',
    noReviewer:
      'Aktuell ist kein unabhängiger Prüfer berechtigt. Bitten Sie einen Organisationseigentümer oder Administrator, einen aktiven Eigentümer/Administrator hinzuzufügen oder wieder zu berechtigen, der diese Version nicht verfasst hat.',
    recoverPending:
      'Diese Anfrage bleibt ausstehend. Ein neu berechtigter unabhängiger Prüfer kann sie genehmigen. Für einen weiteren lokalen Testhinweis setzen Sie den Inhalt auf Entwurf zurück und reichen ihn erneut zur Prüfung ein.',
    recoverDraft:
      'Sobald ein unabhängiger Prüfer verfügbar ist, reichen Sie den Inhalt zur Prüfung ein. Dies erteilt keine Berechtigungen und versendet keine Live-E-Mail.',
    administration: 'Organisationsverwaltung öffnen',
    finishEditing:
      'Schließen Sie Inhaltsänderungen ab oder verwerfen Sie sie, bevor Sie die Organisationsverwaltung öffnen.',
  },
  ar: {
    approve: 'اعتماد المراجعة',
    adopt: 'تبني النسخة الحالية',
    review: 'المراجعة',
    pendingOptional: 'مرحلة مراجعة سير العمل — الموافقة المستقلة غير مطلوبة',
    unknownOptional: 'المؤلف غير معروف — الموافقة المستقلة غير مطلوبة',
    policy: 'إصدار السياسة',
    authorship_unknown: 'المؤلف غير معروف',
    approved: 'معتمد',
    pending: 'بانتظار موافقة مستقلة',
    not_requested: 'لم تُطلب',
    unavailable: 'معلومات المراجعة غير متاحة',
    required:
      'يتطلب النشر الجديد أو المعدل موافقة مستقلة صالحة. تبقى النسخ المنشورة الحالية دون تغيير.',
    optional: 'لا تتطلب السياسة الحالية مراجعة.',
    adapter:
      'تستخدم إشعارات المراجعة محول اختبار محليًا فقط: إيصالات اختبار محفوظة وليست بريدًا فعليًا. قد تُبطل تغييرات السياسة أو المحتوى الموافقة.',
    adoption:
      'أقر بأن النسخة الكاملة هي محتوى من تأليفي. يؤدي ذلك إلى إنشاء مسودة جديدة ولا ينشرها مطلقًا.',
    approval: 'يجب أن تكون الموافقة مستقلة عن مؤلفي هذا الإصدار ولا تؤدي إلى النشر بحد ذاتها.',
    uncertain:
      'تعذر تأكيد التغيير أو تغير المحتوى في مكان آخر. تم الاحتفاظ بالمسودة. أعد التحميل قبل أي تعديل آخر؛ ربما اكتمل التغيير بالفعل.',
    reload: 'تجاهل المسودة وأعد تحميل المحتوى',
    noReviewer:
      'لا يوجد حاليًا مراجع مستقل مؤهل. اطلب من مالك المؤسسة أو مسؤولها إضافة مالك أو مسؤول نشط لم يؤلف هذا الإصدار أو استعادة أهليته.',
    recoverPending:
      'يبقى هذا الطلب معلقًا. يمكن لمراجع مستقل مؤهل حديثًا اعتماده. لطلب إشعار اختبار محلي جديد، أعد المحتوى إلى مسودة ثم أرسله للمراجعة مجددًا.',
    recoverDraft:
      'بعد توفر مراجع مستقل، أرسل المحتوى للمراجعة. لا يمنح ذلك أذونات ولا يرسل بريدًا فعليًا.',
    administration: 'فتح إدارة المؤسسة',
    finishEditing: 'أكمل تعديلات المحتوى أو تجاهلها قبل فتح إدارة المؤسسة.',
  },
};
