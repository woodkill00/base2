from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID, uuid4

from api.db import db_conn
from api.security.content_workspace import CursorCodec, CursorError, canonical_digest
from api.settings import settings


FILTER_OPERATORS = {
    'short_text': {'eq', 'ne', 'contains', 'starts_with', 'in', 'is_null'},
    'long_text': {'eq', 'ne', 'contains', 'is_null'},
    'integer': {'eq', 'ne', 'lt', 'lte', 'gt', 'gte', 'in', 'is_null'},
    'decimal': {'eq', 'ne', 'lt', 'lte', 'gt', 'gte', 'in', 'is_null'},
    'date': {'eq', 'ne', 'lt', 'lte', 'gt', 'gte', 'is_null'},
    'datetime': {'eq', 'ne', 'lt', 'lte', 'gt', 'gte', 'is_null'},
    'boolean': {'eq', 'ne', 'is_null'},
    'slug': {'eq', 'ne', 'starts_with', 'in', 'is_null'},
    'enum': {'eq', 'ne', 'in', 'is_null'},
}


def compile_filters(filters: list[dict[str, Any]], allowed_fields: dict[str, str]):
    if not isinstance(filters, list) or len(filters) > 16:
        raise ValueError('content_query_invalid')
    clauses: list[str] = []
    params: list[Any] = []
    for item in filters:
        if not isinstance(item, dict) or set(item) != {'field', 'operator', 'value'}:
            raise ValueError('content_query_invalid')
        field = item['field']
        operator = item['operator']
        field_kind = allowed_fields.get(field)
        if field_kind is None or operator not in FILTER_OPERATORS.get(field_kind, set()):
            raise ValueError('content_query_invalid')
        expression = 'values ->> %s'
        params.append(field)
        if operator == 'contains':
            clauses.append(f'{expression} ILIKE %s')
            params.append(f"%{item['value']}%")
        elif operator == 'starts_with':
            clauses.append(f'{expression} ILIKE %s')
            params.append(f"{item['value']}%")
        elif operator == 'is_null':
            clauses.append(f"{expression} IS {'NOT ' if item['value'] is False else ''}NULL")
        elif operator == 'in':
            if not isinstance(item['value'], list) or not 1 <= len(item['value']) <= 50:
                raise ValueError('content_query_invalid')
            clauses.append(f'{expression} = ANY(%s)')
            params.append([str(value) for value in item['value']])
        else:
            sql_operator = {'eq': '=', 'ne': '<>', 'lt': '<', 'lte': '<=', 'gt': '>', 'gte': '>='}[
                operator
            ]
            clauses.append(f'{expression} {sql_operator} %s')
            params.append(str(item['value']))
    return ' AND '.join(clauses), params


def _definition(row) -> dict[str, Any]:
    return {
        'id': row[0],
        'siteId': row[1],
        'typeKey': row[2],
        'version': row[3],
        'name': row[4],
        'description': row[5],
        'status': row[6],
        'lockVersion': row[7],
    }


def _record(row) -> dict[str, Any]:
    return {
        'id': str(row[0]),
        'siteId': row[1],
        'typeKey': row[2],
        'slug': row[3],
        'title': row[4],
        'values': row[5],
        'state': row[6],
        'schemaVersion': row[7],
        'version': row[8],
        'updatedAt': row[9].isoformat() if hasattr(row[9], 'isoformat') else row[9],
    }


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def _validate_values(values: dict[str, Any], fields: list[tuple]) -> None:
    declared = {row[0]: row for row in fields}
    if len(values) > 128 or set(values) - set(declared):
        raise ValueError('content_schema_invalid')
    for field_key, field_kind, required, nullable, _validation in fields:
        if field_key not in values:
            if required:
                raise ValueError('content_schema_invalid')
            continue
        value = values[field_key]
        if value is None and not nullable:
            raise ValueError('content_schema_invalid')
        if value is None:
            continue
        valid = {
            'short_text': isinstance(value, str),
            'long_text': isinstance(value, str),
            'rich_text': isinstance(value, dict),
            'integer': isinstance(value, int) and not isinstance(value, bool),
            'decimal': isinstance(value, (str, int)) and not isinstance(value, bool),
            'boolean': isinstance(value, bool),
            'date': isinstance(value, str),
            'datetime': isinstance(value, str),
            'enum': isinstance(value, str),
            'slug': isinstance(value, str),
            'url': isinstance(value, str),
            'email': isinstance(value, str),
            'location': isinstance(value, dict),
            'reference': isinstance(value, str),
            'references': isinstance(value, list),
            'image': isinstance(value, str),
            'file': isinstance(value, str),
            'json_object': isinstance(value, dict),
        }.get(field_kind, False)
        if not valid:
            raise ValueError('content_schema_invalid')


def _audit(cur, *, site_id: str, actor_ref: str, object_type: str, object_ref: str, action: str):
    cur.execute(
        """INSERT INTO sitecontent_workspaceauditevent
           (id, site_id, actor_ref, object_type, object_ref, action, outcome,
            correlation_id, metadata, created_at)
           VALUES (%s,%s,%s,%s,%s,%s,'accepted','',%s::jsonb,NOW())""",
        (str(uuid4()), site_id, actor_ref, object_type, object_ref, action, '{}'),
    )


class PostgresContentWorkspaceRepository:
    def list_definitions(self, *, site_id: str, limit: int, cursor: UUID | None):
        cursor_clause = 'AND id > %s' if cursor else ''
        params: list[Any] = [site_id]
        if cursor:
            params.append(str(cursor))
        params.append(limit + 1)
        with db_conn(tenant_id=site_id) as conn, conn.cursor() as cur:
            cur.execute(
                f"""SELECT id, site_id, type_key, version, name, description, status, lock_version
                    FROM sitecontent_contenttypedefinition
                    WHERE site_id=%s {cursor_clause}
                    ORDER BY type_key, version, id
                    LIMIT %s""",
                tuple(params),
            )
            rows = cur.fetchall()
        items = [_definition(row) for row in rows[:limit]]
        return {
            'items': items,
            'nextCursor': str(items[-1]['id']) if len(rows) > limit else None,
        }

    def create_definition(self, *, site_id: str, actor_ref: str, payload: dict[str, Any]):
        definition_id = uuid4()
        with db_conn(tenant_id=site_id) as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO sitecontent_contenttypedefinition
                           (id, site_id, type_key, version, name, description, status,
                            preset_id, preset_version, compatibility, migration_digest,
                            lock_version, created_by, updated_by, created_at, updated_at)
                           VALUES (%s,%s,%s,1,%s,%s,'draft',%s,1,'additive','',1,%s,%s,NOW(),NOW())
                           RETURNING id, version, status, lock_version""",
                        (
                            str(definition_id),
                            site_id,
                            payload['type_key'],
                            payload['name'],
                            payload.get('description', ''),
                            payload.get('preset_id', 'custom'),
                            actor_ref,
                            actor_ref,
                        ),
                    )
                    created = cur.fetchone()
                    for order, field in enumerate(payload.get('fields', [])):
                        cur.execute(
                            """INSERT INTO sitecontent_contentfielddefinition
                               (id, definition_id, field_key, label, description, field_kind,
                                "order", required, nullable, default_value, validation,
                                presentation, indexed, "unique", read_permission, write_permission)
                               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,
                                       %s,%s,%s,%s)""",
                            (
                                str(uuid4()),
                                str(definition_id),
                                field['field_key'],
                                field['label'],
                                field.get('description', ''),
                                field['field_kind'],
                                order,
                                field.get('required', False),
                                field.get('nullable', False),
                                _json(field.get('default_value')),
                                _json(field.get('validation', {})),
                                _json(field.get('presentation', {})),
                                field.get('indexed', False),
                                field.get('unique', False),
                                field.get('read_permission', 'content.read'),
                                field.get('write_permission', 'content.write'),
                            ),
                        )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return {
            'id': created[0],
            'siteId': site_id,
            'typeKey': payload['type_key'],
            'version': created[1],
            'status': created[2],
            'lockVersion': created[3],
        }

    @staticmethod
    def _schema(cur, *, site_id: str, type_key: str):
        cur.execute(
            """SELECT id, version FROM sitecontent_contenttypedefinition
               WHERE site_id=%s AND type_key=%s AND status='published'
               ORDER BY version DESC LIMIT 1""",
            (site_id, type_key),
        )
        definition = cur.fetchone()
        if not definition:
            raise ValueError('content_not_found')
        cur.execute(
            """SELECT field_key, field_kind, required, nullable, validation
               FROM sitecontent_contentfielddefinition WHERE definition_id=%s
               ORDER BY "order", field_key""",
            (str(definition[0]),),
        )
        return definition, cur.fetchall()

    def list_records(self, *, site_id: str, type_key: str, limit: int, cursor: str | None):
        scope = {
            'site': site_id,
            'type': type_key,
            'query': canonical_digest({'sort': ['slug', 'id']}),
            'limit': limit,
        }
        codec = CursorCodec(str(settings.TOKEN_PEPPER))
        position = None
        if cursor:
            try:
                position = codec.decode(cursor, expected_scope=scope)
            except CursorError as exc:
                raise ValueError('content_query_invalid') from exc
        params: list[Any] = [site_id, type_key]
        position_clause = ''
        if position:
            position_clause = 'AND (slug, id) > (%s, %s)'
            params.extend([position.get('slug'), position.get('id')])
        params.append(limit + 1)
        with db_conn(tenant_id=site_id) as conn, conn.cursor() as cur:
            cur.execute(
                f"""SELECT id, site_id, content_type, slug, title, values, state,
                           schema_version, version, updated_at
                    FROM sitecontent_contentrecord
                    WHERE site_id=%s AND content_type=%s AND deleted_at IS NULL {position_clause}
                    ORDER BY slug, id LIMIT %s""",
                tuple(params),
            )
            rows = cur.fetchall()
        items = [_record(row) for row in rows[:limit]]
        next_cursor = None
        if len(rows) > limit:
            last = items[-1]
            next_cursor = codec.encode(
                scope=scope, position={'slug': last['slug'], 'id': last['id']}
            )
        return {'items': items, 'nextCursor': next_cursor}

    def create_record(self, *, site_id: str, type_key: str, actor_ref: str, payload: dict):
        record_id = uuid4()
        with db_conn(tenant_id=site_id) as conn:
            try:
                with conn.cursor() as cur:
                    definition, fields = self._schema(cur, site_id=site_id, type_key=type_key)
                    _validate_values(payload['values'], fields)
                    cur.execute(
                        """INSERT INTO sitecontent_contentrecord
                           (id, site_id, content_type, slug, title, excerpt, body, metadata,
                            state, publish_at, published_at, sitemap_include, search_visible,
                            version, definition_id, schema_version, values, deleted_at,
                            created_at, updated_at)
                           VALUES (%s,%s,%s,%s,%s,'','',%s::jsonb,'draft',NULL,NULL,TRUE,TRUE,
                                   1,%s,%s,%s::jsonb,NULL,NOW(),NOW())
                           RETURNING id, site_id, content_type, slug, title, values, state,
                                     schema_version, version, updated_at""",
                        (
                            str(record_id),
                            site_id,
                            type_key,
                            payload['slug'],
                            payload['title'],
                            '{}',
                            str(definition[0]),
                            definition[1],
                            _json(payload['values']),
                        ),
                    )
                    row = cur.fetchone()
                    _audit(
                        cur,
                        site_id=site_id,
                        actor_ref=actor_ref,
                        object_type='content_record',
                        object_ref=str(record_id),
                        action='content.create',
                    )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return _record(row)

    def update_record(
        self,
        *,
        site_id: str,
        type_key: str,
        record_id: UUID,
        expected_version: int,
        actor_ref: str,
        values: dict,
    ):
        with db_conn(tenant_id=site_id) as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """SELECT id, version, schema_version, values
                           FROM sitecontent_contentrecord
                           WHERE id=%s AND site_id=%s AND content_type=%s AND deleted_at IS NULL
                           FOR UPDATE""",
                        (str(record_id), site_id, type_key),
                    )
                    existing = cur.fetchone()
                    if not existing:
                        raise ValueError('content_not_found')
                    if existing[1] != expected_version:
                        raise ValueError('content_version_conflict')
                    _definition_row, fields = self._schema(cur, site_id=site_id, type_key=type_key)
                    _validate_values(values, fields)
                    snapshot_json = _json(existing[3])
                    cur.execute(
                        """INSERT INTO sitecontent_contentrevision
                           (id, content_id, revision, snapshot, actor_ref, created_at,
                            schema_version, snapshot_sha256, action, restored_from_version)
                           VALUES (%s,%s,%s,%s::jsonb,%s,NOW(),%s,%s,'update',NULL)""",
                        (
                            str(uuid4()),
                            str(record_id),
                            existing[1],
                            snapshot_json,
                            actor_ref,
                            existing[2],
                            hashlib.sha256(snapshot_json.encode()).hexdigest(),
                        ),
                    )
                    cur.execute(
                        """UPDATE sitecontent_contentrecord SET values=%s::jsonb,
                           version=version+1, updated_at=NOW()
                           WHERE id=%s AND site_id=%s
                           RETURNING id, site_id, content_type, slug, title, values, state,
                                     schema_version, version, updated_at""",
                        (_json(values), str(record_id), site_id),
                    )
                    row = cur.fetchone()
                    _audit(
                        cur,
                        site_id=site_id,
                        actor_ref=actor_ref,
                        object_type='content_record',
                        object_ref=str(record_id),
                        action='content.update',
                    )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return _record(row)

    def transition_record(
        self,
        *,
        site_id: str,
        type_key: str,
        record_id: UUID,
        expected_version: int,
        actor_ref: str,
        action: str,
        publish_at,
        timezone: str | None,
    ):
        del timezone  # Reserved for the durable scheduling metadata slice.
        with db_conn(tenant_id=site_id) as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """SELECT r.id, r.version, r.schema_version, r.values, r.state,
                                  w.transitions
                           FROM sitecontent_contentrecord r
                           JOIN sitecontent_workflowdefinition w ON w.definition_id=r.definition_id
                           WHERE r.id=%s AND r.site_id=%s AND r.content_type=%s
                             AND r.deleted_at IS NULL FOR UPDATE""",
                        (str(record_id), site_id, type_key),
                    )
                    existing = cur.fetchone()
                    if not existing:
                        raise ValueError('content_not_found')
                    if existing[1] != expected_version:
                        raise ValueError('content_version_conflict')
                    transition = next(
                        (
                            item
                            for item in existing[5]
                            if item.get('action') == action and existing[4] in item.get('from', [])
                        ),
                        None,
                    )
                    if not transition:
                        raise ValueError('content_transition_invalid')
                    destination = transition['to']
                    if destination == 'scheduled' and publish_at is None:
                        raise ValueError('content_transition_invalid')
                    snapshot_json = _json(existing[3])
                    cur.execute(
                        """INSERT INTO sitecontent_contentrevision
                           (id, content_id, revision, snapshot, actor_ref, created_at,
                            schema_version, snapshot_sha256, action, restored_from_version)
                           VALUES (%s,%s,%s,%s::jsonb,%s,NOW(),%s,%s,%s,NULL)""",
                        (
                            str(uuid4()),
                            str(record_id),
                            existing[1],
                            snapshot_json,
                            actor_ref,
                            existing[2],
                            hashlib.sha256(snapshot_json.encode()).hexdigest(),
                            action,
                        ),
                    )
                    cur.execute(
                        """UPDATE sitecontent_contentrecord
                           SET state=%s, publish_at=%s,
                               published_at=CASE WHEN %s='published' THEN NOW() ELSE published_at END,
                               deleted_at=CASE WHEN %s='deleted' THEN NOW() ELSE deleted_at END,
                               version=version+1, updated_at=NOW()
                           WHERE id=%s AND site_id=%s
                           RETURNING id, site_id, content_type, slug, title, values, state,
                                     schema_version, version, updated_at""",
                        (
                            destination,
                            publish_at if destination == 'scheduled' else None,
                            destination,
                            destination,
                            str(record_id),
                            site_id,
                        ),
                    )
                    row = cur.fetchone()
                    _audit(
                        cur,
                        site_id=site_id,
                        actor_ref=actor_ref,
                        object_type='content_record',
                        object_ref=str(record_id),
                        action=f'content.{action}',
                    )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return _record(row)

    def soft_delete_record(self, **kwargs):
        return self.transition_record(action='delete', publish_at=None, timezone=None, **kwargs)
