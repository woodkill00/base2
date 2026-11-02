"""Canonical explicit-public-copy contract; SQLite is not PostgreSQL policy proof."""

import pytest
from django.core.exceptions import ValidationError

from common.models import validate_public_content
from sitecontent.models import ContentRecord, ContentRevision
from tests.test_content_workspace_models import published_definition_with_title

pytestmark = pytest.mark.django_db


def record():
    return ContentRecord.objects.create(
        site_id="site-a",
        content_type="article",
        slug="public-copy",
        title="Public title",
        definition=published_definition_with_title(),
        values={"title": "PRIVATE"},
        excerpt="Old excerpt",
        body="Old body",
        metadata={"forensic": "retain"},
    )


@pytest.mark.parametrize(
    "value",
    [
        None,
        {},
        {"excerpt": ""},
        {"excerpt": "", "body": "", "metadata": {}},
        {"excerpt": 1, "body": ""},
        {"excerpt": "", "body": None},
        {"excerpt": "\0", "body": ""},
        {"excerpt": "", "body": "\ud800"},
        {"excerpt": "x" * 2001, "body": ""},
        {"excerpt": "", "body": "x" * 20001},
    ],
)
def test_public_copy_rejects_invalid_input(value):
    with pytest.raises(ValidationError, match="content_public_content_invalid"):
        validate_public_content(value)


def test_public_copy_preserves_literal_text_and_unicode_codepoints():
    validate_public_content({"excerpt": "😀" * 2000, "body": "😀" * 20000})
    validate_public_content({"excerpt": "<script>literal</script>", "body": "  Keep\n\nspacing  "})


@pytest.mark.parametrize("value", [12, False, None, "\0", "\udfff", "x" * 20001])
def test_full_clean_rejects_native_types_before_textfield_coercion(value):
    item = record()
    item.body = value
    with pytest.raises(ValidationError, match="content_public_content_invalid"):
        item.full_clean()


def test_atomic_public_copy_history_clear_omission_and_restore():
    item = record()
    item.update_values(
        {"title": "Next private"},
        expected_version=1,
        public_content={"excerpt": "<b>text</b>", "body": "New body"},
    )
    item.refresh_from_db()
    first = item.revisions.get(revision=1).snapshot
    assert first["publicContent"] == {"excerpt": "Old excerpt", "body": "Old body"}
    assert first["context"]["metadata"] == {"forensic": "retain"}
    assert first["context"]["title"] == "Public title"
    assert first["context"]["version"] == 1
    item.update_values({"title": "Third private"}, expected_version=2)
    assert item.body == "New body"
    item.update_values(
        {"title": "Third private"}, expected_version=3, public_content={"excerpt": "", "body": ""}
    )
    assert item.body == item.excerpt == ""
    item.restore_version(1, expected_version=4)
    assert item.body == "Old body" and item.values == {"title": "PRIVATE"}
    assert item.version == 5
    with pytest.raises(ValidationError, match="content_version_conflict"):
        item.update_values({}, expected_version=4, public_content={"excerpt": "", "body": ""})
    assert item.revisions.count() == 4


def test_legacy_flat_restore_preserves_copy_and_values_named_field():
    from common.models import read_workspace_snapshot

    values = {"values": {"private": "do not unwrap"}, "body": "PRIVATE"}
    restored, copy, mode = read_workspace_snapshot(values)
    assert restored == values and copy is None and mode == "preserve_current"
    item = record()
    ContentRevision.objects.create(content=item, revision=9, snapshot={"title": "Legacy"})
    item.restore_version(9, expected_version=1)
    assert item.body == "Old body" and item.values == {"title": "Legacy"}


def test_unknown_format_and_legacy_full_context():
    from common.models import read_workspace_snapshot

    with pytest.raises(ValidationError, match="content_version_snapshot_invalid"):
        read_workspace_snapshot({"snapshotFormat": "future", "values": {}})
    legacy = {
        "title": "Historical",
        "values": {"title": "Old"},
        "excerpt": "Old excerpt",
        "body": "Old body",
        "metadata": {},
        "state": "published",
        "publishAt": None,
        "scheduleTimezone": None,
        "sitemapInclude": True,
        "searchVisible": True,
        "version": 1,
    }
    values, copy, mode = read_workspace_snapshot(legacy)
    assert values == {"title": "Old"} and copy["body"] == "Old body" and mode == "snapshot"


@pytest.mark.parametrize(
    "snapshot",
    [
        None,
        {"snapshotFormat": "future"},
        {"publishAt": None, "scheduleTimezone": "", "sitemapInclude": True, "searchVisible": True},
        {"invalid-Key": "not private"},
        {1: "not string"},
        {"snapshotFormat": "workspace-record-v1"},
        {str(i): "too many" for i in range(129)},
    ],
)
def test_malformed_snapshot_fails_closed_and_is_marked_unsupported(snapshot):
    from common.models import read_workspace_snapshot, workspace_snapshot_restore_mode

    with pytest.raises(ValidationError):
        read_workspace_snapshot(snapshot)
    assert workspace_snapshot_restore_mode(snapshot) == "unsupported"


def test_new_envelope_rejects_null_copy_and_invalid_values_and_retains_native_context():
    from common.models import read_workspace_snapshot, workspace_snapshot_restore_mode

    item = record()
    snapshot = item.workspace_snapshot()
    assert workspace_snapshot_restore_mode(snapshot) == "snapshot"
    assert workspace_snapshot_restore_mode({"title": "legacy"}) == "preserve_current"
    for changed in (
        {"publicContent": None},
        {"values": []},
        {"values": {str(i): i for i in range(129)}},
        {"context": {}},
        {"unexpected": True},
    ):
        with pytest.raises(ValidationError):
            read_workspace_snapshot({**snapshot, **changed})
    item.excerpt = 42
    with pytest.raises(ValidationError, match="content_public_content_invalid"):
        item.clean()


def test_api_mirror_and_canonical_helpers_remain_semantically_identical():
    from importlib.util import module_from_spec, spec_from_file_location
    from pathlib import Path

    from common import models as canonical

    # CI runs from django/, where the sibling API package is intentionally not
    # importable. Load only its actual pure contract helper; do not alter sys.path.
    helper_path = Path(__file__).resolve().parents[2] / "api" / "content_public_authoring.py"
    spec = spec_from_file_location("public_content_contract_mirror", helper_path)
    assert spec is not None and spec.loader is not None
    mirror = module_from_spec(spec)
    spec.loader.exec_module(mirror)

    assert canonical.WORKSPACE_SNAPSHOT_CONTEXT == mirror.WORKSPACE_SNAPSHOT_CONTEXT
    assert canonical.PUBLIC_BODY_MAX_LENGTH == mirror.PUBLIC_BODY_MAX_LENGTH
    assert canonical.PUBLIC_EXCERPT_MAX_LENGTH == mirror.PUBLIC_EXCERPT_MAX_LENGTH
    item = record()
    source = {
        column: getattr(item, column)
        for column in {*canonical.WORKSPACE_SNAPSHOT_CONTEXT.values(), "values", "excerpt", "body"}
    }
    assert canonical.workspace_record_snapshot(source) == mirror.workspace_record_snapshot(source)
    snapshot = item.workspace_snapshot()
    assert canonical.read_workspace_snapshot(snapshot) == mirror.read_workspace_snapshot(snapshot)


def test_unmanaged_large_static_revision_diff_and_restore_remain_values_only():
    item = ContentRecord.objects.create(
        site_id="site-a",
        content_type="page",
        slug="static-large",
        title="Static page",
        excerpt="E" * 2001,
        body="B" * 20001,
        values={"note": "Earlier"},
    )
    item.full_clean()  # The new managed-copy bounds do not govern static pages.
    old = item.create_revision()
    assert old.diff_values({"note": "Later"}) == {"added": [], "removed": [], "changed": ["note"]}
    item.version = 2
    item.values = {"note": "Later"}
    item.excerpt = "Keep current excerpt"
    item.body = "Keep current static body"
    item.save()
    item.restore_version(old.revision, expected_version=2)
    assert item.values == {"note": "Earlier"}
    assert item.excerpt == "Keep current excerpt" and item.body == "Keep current static body"
    assert item.revisions.get(revision=2).snapshot == {"note": "Later"}
    item.update_values({"note": "Newest"}, expected_version=3)
    assert item.revisions.get(revision=3).snapshot == {"note": "Earlier"}


def test_managed_legacy_large_copy_still_rejects_restore():
    item = record()
    legacy = {
        "values": {"title": "Old"},
        "excerpt": "",
        "body": "B" * 20001,
        "publishAt": None,
        "scheduleTimezone": "",
        "sitemapInclude": True,
        "searchVisible": True,
    }
    version = ContentRevision.objects.create(content=item, revision=9, snapshot=legacy)
    with pytest.raises(ValidationError, match="content_public_content_invalid"):
        version.diff_values({"title": "Later"})
    with pytest.raises(ValidationError, match="content_public_content_invalid"):
        item.restore_version(9, expected_version=1)
    item.refresh_from_db()
    assert item.version == 1 and item.body == "Old body" and item.revisions.count() == 1
