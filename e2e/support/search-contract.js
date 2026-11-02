const assert = require('node:assert/strict');

// Public /api/search returns SearchDocument IDs, not ContentRecord IDs. The
// stable content projection is urlPath+title within the request's fixed tenant.
function readCompleteSearchPage(payload) {
  assert.ok(payload && typeof payload === 'object' && !Array.isArray(payload));
  assert.ok(Array.isArray(payload.items), 'SearchPage.items must be an array');
  assert.equal(
    payload.nextCursor,
    null,
    'Visibility proof requires a complete, unpaginated result'
  );
  if ('hasMore' in payload) assert.equal(payload.hasMore, false);
  if ('total' in payload) assert.equal(payload.total, payload.items.length);
  assert.ok(
    typeof payload.freshThrough === 'string' && Number.isFinite(Date.parse(payload.freshThrough))
  );
  const ids = new Set();
  for (const item of payload.items) {
    assert.ok(item && typeof item === 'object' && !Array.isArray(item));
    assert.match(item.id, /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i);
    assert.equal(typeof item.title, 'string');
    assert.equal(typeof item.excerpt, 'string');
    assert.ok(typeof item.urlPath === 'string' && item.urlPath.startsWith('/'));
    assert.ok(typeof item.indexedAt === 'string' && Number.isFinite(Date.parse(item.indexedAt)));
    assert.ok(!ids.has(item.id), 'Search page must not duplicate a document');
    ids.add(item.id);
  }
  return payload;
}

function matchingSearchDocuments(page, type, record) {
  return page.items.filter(
    (item) => item.urlPath === `/${type}/${record.slug}` && item.title === record.title
  );
}

module.exports = { readCompleteSearchPage, matchingSearchDocuments };
