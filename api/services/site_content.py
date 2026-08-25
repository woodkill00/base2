from __future__ import annotations

import hashlib
import json
from typing import Any, Protocol
from uuid import UUID

from api.site_manifest import load_runtime_manifest


class SiteContentRepository(Protocol):
    def list_content(self, *, site_id: str, limit: int, cursor: UUID | None) -> dict[str, Any]: ...
    def get_content(
        self, *, site_id: str, content_type: str, slug: str
    ) -> dict[str, Any] | None: ...
    def get_media(self, *, site_id: str, asset_id: UUID) -> dict[str, Any] | None: ...
    def search(
        self, *, site_id: str, query: str, limit: int, cursor: UUID | None
    ) -> dict[str, Any]: ...
    def submit_form(
        self,
        *,
        site_id: str,
        form_key: str,
        replay_key: str,
        payload: dict[str, Any],
        consent: dict[str, Any],
        request_id: str,
        retention_days: int,
        request_digest: str,
    ) -> dict[str, Any]: ...


class SiteContentService:
    def __init__(self, repository: SiteContentRepository):
        self.repository = repository
        self.manifest, _ = load_runtime_manifest()

    @staticmethod
    def _cursor(value: str | None) -> UUID | None:
        if value is None:
            return None
        try:
            return UUID(value)
        except (TypeError, ValueError) as exc:
            raise ValueError('invalid_cursor') from exc

    def list_content(self, *, site_id: str, limit: int, cursor: str | None):
        return self.repository.list_content(
            site_id=site_id, limit=limit, cursor=self._cursor(cursor)
        )

    def get_content(self, *, site_id: str, content_type: str, slug: str):
        return self.repository.get_content(site_id=site_id, content_type=content_type, slug=slug)

    def get_media(self, *, site_id: str, asset_id: UUID):
        return self.repository.get_media(site_id=site_id, asset_id=asset_id)

    def search(self, *, site_id: str, query: str, limit: int, cursor: str | None):
        return self.repository.search(
            site_id=site_id, query=query, limit=limit, cursor=self._cursor(cursor)
        )

    def submit_form(
        self,
        *,
        site_id: str,
        form_key: str,
        replay_key: str,
        payload: dict[str, Any],
        consent: dict[str, Any],
        request_id: str,
    ):
        encoded = json.dumps(
            {'siteId': site_id, 'formKey': form_key, 'payload': payload, 'consent': consent},
            sort_keys=True,
            separators=(',', ':'),
            ensure_ascii=False,
        ).encode()
        request_digest = hashlib.sha256(encoded).hexdigest()
        return self.repository.submit_form(
            site_id=site_id,
            form_key=form_key,
            replay_key=replay_key,
            payload=payload,
            consent=consent,
            request_id=request_id,
            retention_days=int(self.manifest['contact']['retentionDays']),
            request_digest=request_digest,
        )
