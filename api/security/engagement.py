from __future__ import annotations

import re
from typing import Any


class EngagementPolicyError(ValueError):
    pass


CONTROL = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
URL = re.compile(r'https?://|www\.', re.IGNORECASE)
SCRIPT = re.compile(r'<\s*(script|iframe|object|embed)|javascript:', re.IGNORECASE)
TRANSITIONS = {
    'pending': {'published', 'rejected'},
    'published': {'hidden'},
    'hidden': {'published', 'rejected'},
    'rejected': set(),
}


def validate_text(value: Any, *, field: str, minimum: int, maximum: int) -> str:
    if not isinstance(value, str):
        raise EngagementPolicyError(f'{field}:invalid')
    normalized = ' '.join(value.strip().split())
    if not minimum <= len(normalized) <= maximum or CONTROL.search(normalized):
        raise EngagementPolicyError(f'{field}:invalid')
    if SCRIPT.search(normalized):
        raise EngagementPolicyError(f'{field}:active_content')
    return normalized


def community_submission(title: Any, body: Any) -> dict[str, Any]:
    clean_title = validate_text(title, field='title', minimum=3, maximum=160)
    clean_body = validate_text(body, field='body', minimum=10, maximum=10000)
    url_count = len(URL.findall(clean_body))
    repeated = bool(re.search(r'(.{8,})\1\1', clean_body, re.IGNORECASE))
    score = min(100, url_count * 25 + (50 if repeated else 0))
    return {
        'title': clean_title,
        'body': clean_body,
        'moderationStatus': 'pending',
        'abuseScore': score,
        'requiresReview': score >= 50,
    }


def support_submission(subject: Any, message: Any, consent: Any) -> dict[str, Any]:
    if consent is not True:
        raise EngagementPolicyError('consent:required')
    return {
        'subject': validate_text(subject, field='subject', minimum=3, maximum=160),
        'message': validate_text(message, field='message', minimum=10, maximum=10000),
        'visibility': 'private',
        'retentionClass': 'support-request',
    }


def moderate(current: str, target: str, *, reason_code: str) -> dict[str, str]:
    if target not in TRANSITIONS.get(current, set()):
        raise EngagementPolicyError('moderation:invalid_transition')
    if not re.fullmatch(r'[a-z][a-z0-9_]{2,63}', reason_code or ''):
        raise EngagementPolicyError('moderation:invalid_reason')
    return {'from': current, 'to': target, 'reasonCode': reason_code}


def notification_payload(*, record_id: str, event: str) -> dict[str, str]:
    if not re.fullmatch(r'[A-Za-z0-9-]{8,64}', record_id or ''):
        raise EngagementPolicyError('notification:invalid_record')
    if event not in {'community.review_required', 'support.received', 'support.updated'}:
        raise EngagementPolicyError('notification:invalid_event')
    return {'recordId': record_id, 'event': event}
