"""Mirror common.models public-copy semantics without a configured Django runtime."""

import re

CONTENT_IDENTIFIER_PATTERN = r'\A[a-z][a-z0-9_]{1,62}\Z'

# Explicit plain text is separate from private dynamic values and never HTML.
PUBLIC_EXCERPT_MAX_LENGTH = 2_000
PUBLIC_BODY_MAX_LENGTH = 20_000
WORKSPACE_SNAPSHOT_FORMAT = 'workspace-record-v1'
WORKSPACE_SNAPSHOT_CONTEXT = {
    'title': 'title',
    'slug': 'slug',
    'contentType': 'content_type',
    'schemaVersion': 'schema_version',
    'version': 'version',
    'metadata': 'metadata',
    'state': 'state',
    'publishAt': 'publish_at',
    'scheduleTimezone': 'schedule_timezone',
    'publishedAt': 'published_at',
    'sitemapInclude': 'sitemap_include',
    'searchVisible': 'search_visible',
}


def validate_public_content(value) -> None:
    """Validate Unicode scalar text without coercion, normalization or projection."""
    if not isinstance(value, dict) or set(value) != {'excerpt', 'body'}:
        raise ValueError('content_public_content_invalid')
    for key, limit in (('excerpt', PUBLIC_EXCERPT_MAX_LENGTH), ('body', PUBLIC_BODY_MAX_LENGTH)):
        text = value[key]
        if (
            not isinstance(text, str)
            or len(text) > limit
            or '\x00' in text
            or any(0xD800 <= ord(char) <= 0xDFFF for char in text)
        ):
            raise ValueError('content_public_content_invalid')


def workspace_record_snapshot(source: dict) -> dict:
    """Capture persisted pre-mutation context, including private forensic metadata."""
    context = {}
    for key, column in WORKSPACE_SNAPSHOT_CONTEXT.items():
        value = source[column]
        context[key] = value.isoformat() if hasattr(value, 'isoformat') else value
    return {
        'snapshotFormat': WORKSPACE_SNAPSHOT_FORMAT,
        'values': source['values'],
        'publicContent': {'excerpt': source['excerpt'], 'body': source['body']},
        'context': context,
    }


def read_workspace_snapshot(snapshot: dict) -> tuple[dict, dict | None, str]:
    """Legacy flat versions restore private values only and preserve current public copy.

    Context/state is never a restoration instruction. Camel-case structural keys
    cannot collide with valid lowercase private field identifiers.
    """
    if not isinstance(snapshot, dict):
        raise ValueError('content_version_snapshot_invalid')
    public_content = None
    if 'snapshotFormat' in snapshot:
        if (
            snapshot['snapshotFormat'] != WORKSPACE_SNAPSHOT_FORMAT
            or set(snapshot) != {'snapshotFormat', 'values', 'publicContent', 'context'}
            or not isinstance(snapshot['context'], dict)
            or set(snapshot['context']) != set(WORKSPACE_SNAPSHOT_CONTEXT)
        ):
            raise ValueError('content_version_snapshot_invalid')
        values = snapshot['values']
        public_content = snapshot['publicContent']
        validate_public_content(public_content)
    elif {'publishAt', 'scheduleTimezone', 'sitemapInclude', 'searchVisible'} <= set(snapshot):
        if not {'values', 'excerpt', 'body'} <= set(snapshot):
            raise ValueError('content_version_snapshot_invalid')
        values = snapshot['values']
        public_content = {'excerpt': snapshot['excerpt'], 'body': snapshot['body']}
        validate_public_content(public_content)
    else:
        # Fail closed on malformed structural envelopes instead of unwrapping
        # a legitimate private field named values or guessing from body/excerpt.
        if any(
            not isinstance(key, str) or not re.fullmatch(CONTENT_IDENTIFIER_PATTERN, key)
            for key in snapshot
        ):
            raise ValueError('content_version_snapshot_invalid')
        values = snapshot
    if not isinstance(values, dict) or len(values) > 128:
        raise ValueError('content_version_snapshot_invalid')
    return values, public_content, 'snapshot' if public_content is not None else 'preserve_current'


def workspace_snapshot_restore_mode(snapshot: dict) -> str:
    try:
        return read_workspace_snapshot(snapshot)[2]
    except (ValueError, TypeError):
        return 'unsupported'
