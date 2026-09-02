from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


MAX_BYTES = 5_000_000
MAX_ROWS = 10_000
MAX_COLUMNS = 128
MAX_CELL = 20_000
FORMULA_PREFIXES = ('=', '+', '-', '@', '\t', '\r')
MAX_NESTING = 8
MAX_COLLECTION = 256
FIELD_KEY = re.compile(r'^[a-z][a-z0-9_]{1,62}$')


class TransferError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedRows:
    rows: tuple[dict[str, Any], ...]
    sha256: str


@dataclass(frozen=True)
class ImportOutcome:
    ordinal: int
    source_row_sha256: str
    action: str
    exact_match_id: str | None = None
    candidate_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ImportPlan:
    outcomes: tuple[ImportOutcome, ...]
    counters: dict[str, int]


@dataclass(frozen=True)
class EncryptedExport:
    nonce: bytes
    ciphertext: bytes
    sha256: str


def _bounded(source: bytes) -> str:
    if not isinstance(source, bytes) or not source or len(source) > MAX_BYTES:
        raise TransferError('content_limit_exceeded')
    try:
        text = source.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise TransferError('content_schema_invalid') from exc
    if '\x00' in text:
        raise TransferError('content_schema_invalid')
    return text


def _validate_rows(rows: list[Any], digest: str) -> ParsedRows:
    if len(rows) > MAX_ROWS or any(not isinstance(row, dict) for row in rows):
        raise TransferError('content_limit_exceeded')
    normalized: list[dict[str, Any]] = []
    for row in rows:
        if len(row) > MAX_COLUMNS or any(
            not isinstance(key, str)
            or not key
            or len(key) > 63
            or (isinstance(value, str) and len(value) > MAX_CELL)
            for key, value in row.items()
        ):
            raise TransferError('content_schema_invalid')
        for value in row.values():
            _validate_value(value)
        normalized.append(row)
    return ParsedRows(tuple(normalized), digest)


def _validate_value(value: Any, depth: int = 0) -> None:
    if depth > MAX_NESTING:
        raise TransferError('content_limit_exceeded')
    if isinstance(value, str):
        if len(value) > MAX_CELL:
            raise TransferError('content_limit_exceeded')
        return
    if value is None or isinstance(value, (bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise TransferError('content_schema_invalid')
        return
    if isinstance(value, list):
        if len(value) > MAX_COLLECTION:
            raise TransferError('content_limit_exceeded')
        for child in value:
            _validate_value(child, depth + 1)
        return
    if isinstance(value, dict):
        if len(value) > MAX_COLLECTION:
            raise TransferError('content_limit_exceeded')
        for key, child in value.items():
            if not isinstance(key, str) or not key or len(key) > 63:
                raise TransferError('content_schema_invalid')
            _validate_value(child, depth + 1)
        return
    raise TransferError('content_schema_invalid')


def parse_json(source: bytes) -> ParsedRows:
    text = _bounded(source)
    try:
        payload = json.loads(
            text,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                ValueError('non_finite_json_number')
            ),
        )
    except (json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise TransferError('content_schema_invalid') from exc
    if not isinstance(payload, list):
        raise TransferError('content_schema_invalid')
    return _validate_rows(payload, hashlib.sha256(source).hexdigest())


def parse_csv(source: bytes) -> ParsedRows:
    text = _bounded(source)
    try:
        reader = csv.DictReader(io.StringIO(text, newline=''), strict=True)
        headings = reader.fieldnames or []
        if (
            not headings
            or len(headings) > MAX_COLUMNS
            or len(headings) != len(set(headings))
            or any(
                not heading
                or len(heading) > 63
                or any(ord(character) < 32 for character in heading)
                or heading.lstrip(' ').startswith(FORMULA_PREFIXES)
                for heading in headings
            )
        ):
            raise TransferError('content_schema_invalid')
        rows = []
        for position, row in enumerate(reader, start=1):
            if position > MAX_ROWS:
                raise TransferError('content_limit_exceeded')
            if None in row:
                raise TransferError('content_schema_invalid')
            rows.append(dict(row))
    except csv.Error as exc:
        raise TransferError('content_schema_invalid') from exc
    return _validate_rows(rows, hashlib.sha256(source).hexdigest())


def safe_csv_cell(value: Any) -> str:
    rendered = '' if value is None else str(value)
    probe = rendered.lstrip(' ')
    return f"'{rendered}" if probe.startswith(FORMULA_PREFIXES) else rendered


def export_csv(rows: list[dict[str, Any]], fields: list[str]) -> bytes:
    if not fields or len(fields) > MAX_COLUMNS or len(fields) != len(set(fields)):
        raise TransferError('content_schema_invalid')
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction='raise', lineterminator='\n')
    writer.writeheader()
    for row in rows:
        writer.writerow({field: safe_csv_cell(row.get(field)) for field in fields})
    return output.getvalue().encode()


def _match_key(row: dict[str, Any], fields: list[str]) -> tuple[str, ...]:
    return tuple(str(row.get(field, '')).strip().casefold() for field in fields)


def _similarity(left: dict[str, Any], right: dict[str, Any], fields: list[str]) -> float:
    if not fields:
        return 0.0
    return sum(
        SequenceMatcher(
            None,
            str(left.get(field, '')).strip().casefold(),
            str(right.get(field, '')).strip().casefold(),
        ).ratio()
        for field in fields
    ) / len(fields)


def plan_import(
    parsed: ParsedRows,
    *,
    existing: list[dict[str, Any]],
    exact_fields: list[str],
    similarity_fields: list[str],
) -> ImportPlan:
    if (
        not exact_fields
        or len(exact_fields) > 8
        or len(similarity_fields) > 8
        or len(set(exact_fields + similarity_fields)) != len(exact_fields + similarity_fields)
        or any(not FIELD_KEY.fullmatch(field) for field in exact_fields + similarity_fields)
        or any(any(field not in row for field in exact_fields) for row in parsed.rows)
    ):
        raise TransferError('content_schema_invalid')
    if len(existing) > MAX_ROWS:
        raise TransferError('content_limit_exceeded')
    existing_by_key: dict[tuple[str, ...], dict[str, Any]] = {}
    for record in existing:
        record_id = record.get('id')
        if not isinstance(record_id, str) or not record_id:
            raise TransferError('content_schema_invalid')
        key = _match_key(record, exact_fields)
        if key in existing_by_key:
            raise TransferError('content_integrity_failed')
        existing_by_key[key] = record

    seen_source: set[tuple[str, ...]] = set()
    outcomes: list[ImportOutcome] = []
    counters = {'total': len(parsed.rows), 'create': 0, 'update': 0, 'skip': 0, 'review': 0}
    for ordinal, row in enumerate(parsed.rows, start=1):
        row_digest = hashlib.sha256(
            json.dumps(row, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
        ).hexdigest()
        key = _match_key(row, exact_fields)
        exact = existing_by_key.get(key)
        if key in seen_source:
            action, exact_id, candidates = 'skip', exact.get('id') if exact else None, ()
        elif exact:
            action, exact_id, candidates = 'update', exact['id'], ()
        else:
            candidate_ids = tuple(
                record['id']
                for record in existing
                if _similarity(row, record, similarity_fields) >= 0.82
            )[:10]
            action = 'review' if candidate_ids else 'create'
            exact_id, candidates = None, candidate_ids
        seen_source.add(key)
        counters[action] += 1
        outcomes.append(
            ImportOutcome(
                ordinal=ordinal,
                source_row_sha256=row_digest,
                action=action,
                exact_match_id=exact_id,
                candidate_ids=candidates,
            )
        )
    return ImportPlan(tuple(outcomes), counters)


def encrypt_export(plaintext: bytes, *, key: bytes, context: str) -> EncryptedExport:
    if not plaintext or len(plaintext) > MAX_BYTES or len(key) != 32 or not context:
        raise TransferError('content_schema_invalid')
    nonce = os.urandom(12)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, context.encode())
    digest = hashlib.sha256(nonce + ciphertext).hexdigest()
    return EncryptedExport(nonce=nonce, ciphertext=ciphertext, sha256=digest)


def decrypt_export(encrypted: EncryptedExport, *, key: bytes, context: str) -> bytes:
    if (
        len(key) != 32
        or not context
        or hashlib.sha256(encrypted.nonce + encrypted.ciphertext).hexdigest() != encrypted.sha256
    ):
        raise TransferError('content_integrity_failed')
    try:
        return AESGCM(key).decrypt(encrypted.nonce, encrypted.ciphertext, context.encode())
    except (InvalidTag, ValueError) as exc:
        raise TransferError('content_integrity_failed') from exc
