const object = (value) => value !== null && typeof value === 'object' && !Array.isArray(value);
const integer = (value) => Number.isSafeInteger(value) && value >= 1;
const states = new Set(['draft', 'in_review', 'scheduled', 'published', 'archived', 'deleted']);
const actions = new Set([
  'submit_review',
  'return_draft',
  'schedule',
  'publish',
  'archive',
  'restore',
  'delete',
  'approve_review',
  'adopt_review_subject',
]);

const validPublicText = (value, limit) =>
  typeof value === 'string' &&
  Array.from(value).length <= limit &&
  !Array.from(value).some((character) => {
    const code = character.codePointAt(0);
    return code === 0 || (code >= 0xd800 && code <= 0xdfff);
  });

export const validPublicContent = (value) =>
  object(value) &&
  Object.keys(value).length === 2 &&
  validPublicText(value.excerpt, 2000) &&
  validPublicText(value.body, 20000);

export const validWorkspaceReview = (review) =>
  object(review) &&
  ['authorship_unknown', 'approved', 'pending', 'not_requested'].includes(review.status) &&
  typeof review.requiresReview === 'boolean' &&
  Number.isSafeInteger(review.policyVersion) &&
  review.policyVersion >= 0 &&
  (review.semanticRevision === null || typeof review.semanticRevision === 'string') &&
  review.deliveryAdapter === 'local_test' &&
  [null, 'no_independent_reviewer'].includes(review.recoveryReason);

export const validWorkspaceActions = (value) =>
  Array.isArray(value) &&
  value.length <= actions.size &&
  value.every((action) => actions.has(action)) &&
  new Set(value).size === value.length;

// Mutation acknowledgements are deliberately not detail envelopes. Reconciliation
// must include both the full editable snapshot and authoritative review permissions.
// Approval may change review metadata without advancing the record version.
export const readWorkspaceRecord = (value, { recordId, typeKey, siteId, minimumVersion = 1 }) => {
  if (
    !object(value) ||
    value.id !== recordId ||
    typeof value.id !== 'string' ||
    !value.id ||
    value.siteId !== siteId ||
    value.typeKey !== typeKey ||
    typeof value.title !== 'string' ||
    typeof value.slug !== 'string' ||
    !object(value.values) ||
    !validPublicContent(value.publicContent) ||
    !states.has(value.state) ||
    !integer(value.schemaVersion) ||
    !integer(value.version) ||
    value.version < minimumVersion ||
    typeof value.updatedAt !== 'string' ||
    !Number.isFinite(Date.parse(value.updatedAt)) ||
    !validWorkspaceReview(value.review) ||
    !validWorkspaceActions(value.allowedActions)
  )
    throw new Error('content_record_detail_invalid');
  return {
    ...value,
    values: { ...value.values },
    publicContent: { ...value.publicContent },
    review: { ...value.review },
    allowedActions: [...value.allowedActions],
  };
};
