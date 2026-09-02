from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import dataclass
from typing import Any


MAX_BYTES = 5_000_000
MAX_ROWS = 10_000
MAX_COLUMNS = 128
MAX_CELL = 20_000
FORMULA_PREFIXES = ('=', '+', '-', '@', '\t', '\r')


class TransferError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedRows:
    rows: tuple[dict[str, Any], ...]
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
        normalized.append(row)
    return ParsedRows(tuple(normalized), digest)


def parse_json(source: bytes) -> ParsedRows:
    text = _bounded(source)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise TransferError('content_schema_invalid') from exc
    if not isinstance(payload, list):
        raise TransferError('content_schema_invalid')
    return _validate_rows(payload, hashlib.sha256(source).hexdigest())


def parse_csv(source: bytes) -> ParsedRows:
    text = _bounded(source)
    try:
        reader = csv.DictReader(io.StringIO(text, newline=''), strict=True)
        headings = reader.fieldnames or []
        if not headings or len(headings) > MAX_COLUMNS or len(headings) != len(set(headings)):
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
    return f"'{rendered}" if rendered.startswith(FORMULA_PREFIXES) else rendered


def export_csv(rows: list[dict[str, Any]], fields: list[str]) -> bytes:
    if not fields or len(fields) > MAX_COLUMNS or len(fields) != len(set(fields)):
        raise TransferError('content_schema_invalid')
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction='raise', lineterminator='\n')
    writer.writeheader()
    for row in rows:
        writer.writerow({field: safe_csv_cell(row.get(field)) for field in fields})
    return output.getvalue().encode()
