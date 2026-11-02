export function registeredDocumentSequence(state: string, file: string, title: string, route: string): boolean {
  return state === 'volcano-home' && route === '/' &&
    file.replaceAll('\\', '/').endsWith('/e2e/layout/volcano-preservation.spec.ts') &&
    /^original Volcano reference at (390|1440)px$/.test(title);
}

// Explicit registered comparison states; optional after-test diagnostics may be
// nonapplicable in document/off modes. An approved sequence never silently skips.
export function sequenceApplicable(input: {
  comparison: boolean;
  documentScenario?: boolean;
  compact: boolean;
  layout: string | null;
  volcanoRootCount?: number;
  nestedScrollportCount?: number;
  targetCount: number;
  dialogs: number;
  dialogTarget: boolean;
  targetIsDialog: boolean;
  approvedTarget: string | null;
}): boolean {
  if (input.documentScenario) {
    if (input.approvedTarget || input.layout !== null || input.volcanoRootCount !== 0 ||
        input.nestedScrollportCount !== 0 || input.targetCount !== 0 || input.dialogs || input.dialogTarget)
      throw new Error('registered original home document fixture changed');
    return false;
  }
  const kind = input.dialogTarget ? 'dialog' : 'content-scrollport';
  if (input.approvedTarget && input.approvedTarget !== kind)
    throw new Error('approved sequence target kind changed');
  const required =
    Boolean(input.approvedTarget) || input.dialogTarget || (input.comparison && input.compact);
  if (input.dialogTarget) {
    if (input.targetCount !== 1 || !input.targetIsDialog || input.dialogs !== 1)
      throw new Error('required sequence dialog missing or ambiguous');
    return true;
  }
  if (input.dialogs) {
    if (required || input.comparison)
      throw new Error('unexpected dialog obscures registered content state');
    return false;
  }
  if (!required && input.layout !== 'bottom') return false;
  if (input.layout !== 'bottom' || input.targetCount !== 1)
    throw new Error('required nested sequence target missing');
  return true;
}
