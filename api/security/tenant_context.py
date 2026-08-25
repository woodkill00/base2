from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping


TENANT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]{2,62}$")
_SAFE_KEY_PART = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


class TenantBoundaryError(ValueError):
    """Raised when untrusted data cannot establish an exact tenant boundary."""


def canonical_tenant_id(value: object) -> str:
    tenant_id = str(value or "").strip()
    if not TENANT_ID_PATTERN.fullmatch(tenant_id):
        raise TenantBoundaryError("tenant_invalid")
    return tenant_id


def tenant_cache_key(namespace: str, tenant_id: str, *parts: object) -> str:
    """Build a bounded cache key which can never omit its tenant namespace."""

    tenant = canonical_tenant_id(tenant_id)
    if not _SAFE_KEY_PART.fullmatch(str(namespace or "")):
        raise TenantBoundaryError("cache_namespace_invalid")
    encoded = [str(namespace), "tenant", tenant]
    for value in parts:
        part = str(value or "")
        if not _SAFE_KEY_PART.fullmatch(part):
            raise TenantBoundaryError("cache_key_part_invalid")
        encoded.append(part)
    return ":".join(encoded)


@dataclass(frozen=True)
class TenantJobEnvelope:
    """Strict tenant identity carried by every tenant-owned background job."""

    tenant_id: str
    job_id: str
    operation: str

    @classmethod
    def parse(cls, value: Mapping[str, Any]) -> "TenantJobEnvelope":
        if set(value) != {"tenant_id", "job_id", "operation"}:
            raise TenantBoundaryError("job_envelope_invalid")
        tenant_id = canonical_tenant_id(value["tenant_id"])
        job_id = str(value["job_id"] or "")
        operation = str(value["operation"] or "")
        if not _SAFE_KEY_PART.fullmatch(job_id):
            raise TenantBoundaryError("job_id_invalid")
        if not _SAFE_KEY_PART.fullmatch(operation):
            raise TenantBoundaryError("job_operation_invalid")
        return cls(tenant_id=tenant_id, job_id=job_id, operation=operation)

    def as_dict(self) -> dict[str, str]:
        return {
            "tenant_id": self.tenant_id,
            "job_id": self.job_id,
            "operation": self.operation,
        }
