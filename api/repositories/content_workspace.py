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
RICH_TEXT_TYPES = {
    'document',
    'paragraph',
    'heading',
    'text',
    'bullet_list',
    'ordered_list',
    'list_item',
    'blockquote',
    'code_block',
    'hard_break',
    'link',
}
RICH_TEXT_KEYS = {'type', 'text', 'children', 'level', 'href'}


def _valid_rich_text(value: Any, depth: int = 0) -> bool:
    if depth > 8 or not isinstance(value, dict) or set(value) - RICH_TEXT_KEYS:
        return False
    if value.get('type') not in RICH_TEXT_TYPES:
        return False
    text = value.get('text')
    if text is not None and (not isinstance(text, str) or len(text) > 20_000):
        return False
    href = value.get('href')
    if href is not None and not (
        isinstance(href, str) and (href.startswith('https://') or href.startswith('http://'))
    ):
        return False
    children = value.get('children', [])
    return (
        isinstance(children, list)
        and len(children) <= 256
        and all(_valid_rich_text(child, depth + 1) for child in children)
    )


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
    for field_key, field_kind, required, nullable, default_value, _validation in fields:
        if field_key not in values:
            if required and default_value is None:
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
            'rich_text': _valid_rich_text(value),
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
    def list_definitions(self, *, site_id: str, limit: int, cursor: str | None):
        scope = {
            'site': site_id,
            'query': canonical_digest({'sort': ['type_key', 'version', 'id']}),
            'limit': limit,
        }
        codec = CursorCodec(str(settings.TOKEN_PEPPER))
        position = None
        if cursor:
            try:
                position = codec.decode(cursor, expected_scope=scope)
            except CursorError as exc:
                raise ValueError('content_query_invalid') from exc
        cursor_clause = 'AND (type_key, version, id) > (%s, %s, %s)' if position else ''
        params: list[Any] = [site_id]
        if position:
            params.extend([position.get('typeKey'), position.get('version'), position.get('id')])
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
        next_cursor = None
        if len(rows) > limit:
            last = items[-1]
            next_cursor = codec.encode(
                scope=scope,
                position={
                    'typeKey': last['typeKey'],
                    'version': last['version'],
                    'id': str(last['id']),
                },
            )
        return {'items': items, 'nextCursor': next_cursor}

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
                    states = ['draft', 'in_review', 'scheduled', 'published', 'archived', 'deleted']
                    transitions = [
                        {
                            'action': 'submit_review',
                            'from': ['draft'],
                            'to': 'in_review',
                            'permission': 'content.write',
                        },
                        {
                            'action': 'return_draft',
                            'from': ['in_review'],
                            'to': 'draft',
                            'permission': 'content.write',
                        },
                        {
                            'action': 'schedule',
                            'from': ['in_review'],
                            'to': 'scheduled',
                            'permission': 'content.write',
                            'schedulable': True,
                        },
                        {
                            'action': 'publish',
                            'from': ['in_review', 'scheduled'],
                            'to': 'published',
                            'permission': 'content.write',
                        },
                        {
                            'action': 'archive',
                            'from': ['published'],
                            'to': 'archived',
                            'permission': 'content.write',
                        },
                        {
                            'action': 'restore',
                            'from': ['archived'],
                            'to': 'draft',
                            'permission': 'content.write',
                        },
                        {
                            'action': 'delete',
                            'from': ['draft', 'archived'],
                            'to': 'deleted',
                            'permission': 'content.write',
                        },
                    ]
                    cur.execute(
                        """INSERT INTO sitecontent_workflowdefinition
                           (id, definition_id, states, initial_state, transitions)
                           VALUES (%s,%s,%s::jsonb,'draft',%s::jsonb)""",
                        (str(uuid4()), str(definition_id), _json(states), _json(transitions)),
                    )
                    _audit(
                        cur,
                        site_id=site_id,
                        actor_ref=actor_ref,
                        object_type='content_type',
                        object_ref=str(definition_id),
                        action='content.definition_create',
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

    def get_definition(self, *, site_id: str, type_key: str, version: int):
        with db_conn(tenant_id=site_id) as conn, conn.cursor() as cur:
            cur.execute(
                """SELECT id, site_id, type_key, version, name, description, status, lock_version
                   FROM sitecontent_contenttypedefinition
                   WHERE site_id=%s AND type_key=%s AND version=%s""",
                (site_id, type_key, version),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError('content_not_found')
            cur.execute(
                """SELECT field_key, label, field_kind, required, nullable, default_value,
                          validation, presentation, indexed, "unique", read_permission, write_permission
                   FROM sitecontent_contentfielddefinition WHERE definition_id=%s
                   ORDER BY "order", field_key""",
                (str(row[0]),),
            )
            fields = [
                {
                    'fieldKey': item[0],
                    'label': item[1],
                    'fieldKind': item[2],
                    'required': item[3],
                    'nullable': item[4],
                    'defaultValue': item[5],
                    'validation': item[6],
                    'presentation': item[7],
                    'indexed': item[8],
                    'unique': item[9],
                    'readPermission': item[10],
                    'writePermission': item[11],
                }
                for item in cur.fetchall()
            ]
        return {**_definition(row), 'fields': fields}

    @staticmethod
    def _preview(cur, *, site_id: str, type_key: str, version: int):
        cur.execute(
            """SELECT id FROM sitecontent_contenttypedefinition
               WHERE site_id=%s AND type_key=%s AND version=%s""",
            (site_id, type_key, version),
        )
        current = cur.fetchone()
        if not current:
            raise ValueError('content_not_found')
        cur.execute(
            """SELECT id FROM sitecontent_contenttypedefinition
               WHERE site_id=%s AND type_key=%s AND status='published' AND version<%s
               ORDER BY version DESC LIMIT 1""",
            (site_id, type_key, version),
        )
        previous = cur.fetchone()

        def fields(definition_id):
            if not definition_id:
                return {}
            cur.execute(
                """SELECT field_key, field_kind, required, nullable, validation
                   FROM sitecontent_contentfielddefinition WHERE definition_id=%s""",
                (str(definition_id),),
            )
            return {row[0]: row[1:] for row in cur.fetchall()}

        current_fields = fields(current[0])
        previous_fields = fields(previous[0] if previous else None)
        removed = sorted(set(previous_fields) - set(current_fields))
        added = sorted(set(current_fields) - set(previous_fields))
        changed = sorted(
            key
            for key in set(current_fields) & set(previous_fields)
            if current_fields[key] != previous_fields[key]
        )
        backfill = sorted(key for key in added if previous and current_fields[key][1] is True)
        classification = (
            'lossy' if removed or changed else 'backfill_required' if backfill else 'additive'
        )
        result = {
            'classification': classification,
            'addedFields': added,
            'removedFields': removed,
            'changedFields': changed,
            'backfillFields': backfill,
        }
        result['digest'] = canonical_digest(result)
        result['mutated'] = False
        return result

    def preview_definition(self, *, site_id: str, type_key: str, version: int):
        with db_conn(tenant_id=site_id) as conn, conn.cursor() as cur:
            return self._preview(cur, site_id=site_id, type_key=type_key, version=version)

    def publish_definition(
        self,
        *,
        site_id: str,
        type_key: str,
        version: int,
        expected_lock_version: int,
        confirm_lossy: bool,
        actor_ref: str,
    ):
        with db_conn(tenant_id=site_id) as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """SELECT id, status, lock_version FROM sitecontent_contenttypedefinition
                           WHERE site_id=%s AND type_key=%s AND version=%s FOR UPDATE""",
                        (site_id, type_key, version),
                    )
                    row = cur.fetchone()
                    if not row:
                        raise ValueError('content_not_found')
                    if row[1] != 'draft':
                        raise ValueError('content_schema_incompatible')
                    if row[2] != expected_lock_version:
                        raise ValueError('content_version_conflict')
                    preview = self._preview(
                        cur, site_id=site_id, type_key=type_key, version=version
                    )
                    if (
                        preview['classification'] in {'lossy', 'backfill_required'}
                        and not confirm_lossy
                    ):
                        raise ValueError('lossy_confirmation_required')
                    cur.execute(
                        """UPDATE sitecontent_contenttypedefinition
                           SET status='published', compatibility=%s, migration_digest=%s,
                               published_at=NOW(), lock_version=lock_version+1,
                               updated_by=%s, updated_at=NOW()
                           WHERE id=%s RETURNING type_key, version, status, lock_version""",
                        (preview['classification'], preview['digest'], actor_ref, str(row[0])),
                    )
                    updated = cur.fetchone()
                    _audit(
                        cur,
                        site_id=site_id,
                        actor_ref=actor_ref,
                        object_type='content_type',
                        object_ref=str(row[0]),
                        action='content.definition_publish',
                    )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return {
            'typeKey': updated[0],
            'version': updated[1],
            'status': updated[2],
            'lockVersion': updated[3],
        }

    def retire_definition(
        self,
        *,
        site_id: str,
        type_key: str,
        version: int,
        expected_lock_version: int,
        actor_ref: str,
    ):
        with db_conn(tenant_id=site_id) as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """UPDATE sitecontent_contenttypedefinition
                           SET status='retired', lock_version=lock_version+1,
                               updated_by=%s, updated_at=NOW()
                           WHERE site_id=%s AND type_key=%s AND version=%s
                             AND status='published' AND lock_version=%s
                           RETURNING id, type_key, version, status, lock_version""",
                        (actor_ref, site_id, type_key, version, expected_lock_version),
                    )
                    updated = cur.fetchone()
                    if not updated:
                        raise ValueError('content_version_conflict')
                    _audit(
                        cur,
                        site_id=site_id,
                        actor_ref=actor_ref,
                        object_type='content_type',
                        object_ref=str(updated[0]),
                        action='content.definition_retire',
                    )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return {
            'typeKey': updated[1],
            'version': updated[2],
            'status': updated[3],
            'lockVersion': updated[4],
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
            """SELECT field_key, field_kind, required, nullable, default_value, validation
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

    def list_versions(self, *, site_id: str, type_key: str, record_id: UUID):
        with db_conn(tenant_id=site_id) as conn, conn.cursor() as cur:
            cur.execute(
                """SELECT v.revision, v.schema_version, v.snapshot_sha256, v.action,
                          v.restored_from_version, v.created_at
                   FROM sitecontent_contentrevision v
                   JOIN sitecontent_contentrecord r ON r.id=v.content_id
                   WHERE r.id=%s AND r.site_id=%s AND r.content_type=%s
                   ORDER BY v.revision DESC LIMIT 100""",
                (str(record_id), site_id, type_key),
            )
            rows = cur.fetchall()
        return {
            'items': [
                {
                    'version': row[0],
                    'schemaVersion': row[1],
                    'snapshotSha256': row[2],
                    'action': row[3],
                    'restoredFromVersion': row[4],
                    'createdAt': row[5].isoformat(),
                }
                for row in rows
            ]
        }

    def restore_record(
        self,
        *,
        site_id: str,
        type_key: str,
        record_id: UUID,
        version: int,
        expected_version: int,
        actor_ref: str,
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
                    current = cur.fetchone()
                    if not current:
                        raise ValueError('content_not_found')
                    if current[1] != expected_version:
                        raise ValueError('content_version_conflict')
                    cur.execute(
                        """SELECT snapshot FROM sitecontent_contentrevision
                           WHERE content_id=%s AND revision=%s""",
                        (str(record_id), version),
                    )
                    restored = cur.fetchone()
                    if not restored:
                        raise ValueError('content_not_found')
                    restored_values = restored[0].get('values', restored[0])
                    _definition_row, fields = self._schema(cur, site_id=site_id, type_key=type_key)
                    _validate_values(restored_values, fields)
                    snapshot_json = _json(current[3])
                    cur.execute(
                        """INSERT INTO sitecontent_contentrevision
                           (id, content_id, revision, snapshot, actor_ref, created_at,
                            schema_version, snapshot_sha256, action, restored_from_version)
                           VALUES (%s,%s,%s,%s::jsonb,%s,NOW(),%s,%s,'restore',%s)""",
                        (
                            str(uuid4()),
                            str(record_id),
                            current[1],
                            snapshot_json,
                            actor_ref,
                            current[2],
                            hashlib.sha256(snapshot_json.encode()).hexdigest(),
                            version,
                        ),
                    )
                    cur.execute(
                        """UPDATE sitecontent_contentrecord SET values=%s::jsonb,
                           version=version+1, updated_at=NOW()
                           WHERE id=%s AND site_id=%s
                           RETURNING id, site_id, content_type, slug, title, values, state,
                                     schema_version, version, updated_at""",
                        (_json(restored_values), str(record_id), site_id),
                    )
                    row = cur.fetchone()
                    _audit(
                        cur,
                        site_id=site_id,
                        actor_ref=actor_ref,
                        object_type='content_record',
                        object_ref=str(record_id),
                        action='content.restore',
                    )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return _record(row)

    def list_views(self, *, site_id: str, type_key: str, owner_ref: str):
        with db_conn(tenant_id=site_id) as conn, conn.cursor() as cur:
            cur.execute(
                """SELECT v.id, v.title, v.query, v.visibility, v.shared_roles,
                          v.schema_version, v.lock_version
                   FROM sitecontent_savedview v
                   JOIN sitecontent_contenttypedefinition d ON d.id=v.definition_id
                   WHERE v.site_id=%s AND d.site_id=%s AND d.type_key=%s
                     AND (v.owner_ref=%s OR v.visibility='role_shared')
                   ORDER BY v.title, v.id LIMIT 100""",
                (site_id, site_id, type_key, owner_ref),
            )
            rows = cur.fetchall()
        return {
            'items': [
                {
                    'id': str(row[0]),
                    'title': row[1],
                    'query': row[2],
                    'visibility': row[3],
                    'sharedRoles': row[4],
                    'schemaVersion': row[5],
                    'lockVersion': row[6],
                }
                for row in rows
            ]
        }

    def create_view(self, *, site_id: str, type_key: str, owner_ref: str, payload: dict):
        view_id = uuid4()
        with db_conn(tenant_id=site_id) as conn:
            try:
                with conn.cursor() as cur:
                    definition, fields = self._schema(cur, site_id=site_id, type_key=type_key)
                    allowed = {row[0]: row[1] for row in fields}
                    query = payload['query']
                    compile_filters(query.get('filters', []), allowed)
                    if any(field not in allowed for field in query.get('fields', [])):
                        raise ValueError('content_query_invalid')
                    cur.execute(
                        """INSERT INTO sitecontent_savedview
                           (id, site_id, definition_id, owner_ref, title, query, visibility,
                            shared_roles, schema_version, lock_version, created_at, updated_at)
                           VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s,%s::jsonb,%s,1,NOW(),NOW())
                           RETURNING id, title, visibility, schema_version, lock_version""",
                        (
                            str(view_id),
                            site_id,
                            str(definition[0]),
                            owner_ref,
                            payload['title'],
                            _json(query),
                            payload['visibility'],
                            _json(payload['shared_roles']),
                            definition[1],
                        ),
                    )
                    row = cur.fetchone()
                    _audit(
                        cur,
                        site_id=site_id,
                        actor_ref=owner_ref,
                        object_type='saved_view',
                        object_ref=str(view_id),
                        action='content.view_create',
                    )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return {
            'id': str(row[0]),
            'title': row[1],
            'visibility': row[2],
            'schemaVersion': row[3],
            'lockVersion': row[4],
        }
