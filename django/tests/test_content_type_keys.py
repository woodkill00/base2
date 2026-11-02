from importlib import import_module

import pytest
from django.core.exceptions import ValidationError

from sitecontent.models import (
    AssetBinding,
    ContentFieldDefinition,
    ContentRecord,
    ContentRelationship,
    ContentTypeDefinition,
)

VALID = ["blog-post", "doc-page", "portfolio-item", "old_type", "a_", "a" * 63]
INVALID = [
    "a",
    "a" * 64,
    "Blog-post",
    "-blog",
    "blog-",
    "blog--post",
    "blog-_post",
    "../blog",
    "blog/post",
    "blog\\post",
    "blog post",
    "blog;drop",
    "blog'post",
    "blog\n",
    "blög",
    "blog\u200bpost",
    "blog%2fpost",
    "blog\x00post",
]


@pytest.mark.django_db
@pytest.mark.parametrize("key", VALID)
def test_supported_definition_creation_and_relationship_target(key):
    definition = ContentTypeDefinition.objects.create(site_id="site-a", type_key=key, name="Family")
    assert ContentTypeDefinition.objects.get(pk=definition.pk).type_key == key
    field = ContentFieldDefinition(
        definition=definition,
        field_key="related",
        label="Related",
        field_kind="reference",
        validation={"targetType": key},
    )
    field.save()
    definition.publish(expected_lock_version=1)
    source = ContentRecord.objects.create(
        site_id="site-a", content_type=key, slug="source", title="Source", definition=definition
    )
    target = ContentRecord.objects.create(
        site_id="site-a", content_type=key, slug="target", title="Target", definition=definition
    )
    relation = ContentRelationship.objects.create(
        site_id="site-a", source=source, target=target, field_key="related", target_type=key
    )
    assert relation.target.content_type == key
    ContentRelationship._meta.get_field("target_type").run_validators(key)


@pytest.mark.parametrize("key", INVALID)
def test_type_keys_reject_unsafe_or_malformed_names(key):
    with pytest.raises(ValidationError):
        ContentTypeDefinition._meta.get_field("type_key").run_validators(key)


@pytest.mark.parametrize(
    "model,field",
    [
        (ContentTypeDefinition, "preset_id"),
        (ContentFieldDefinition, "field_key"),
        (ContentRelationship, "field_key"),
        (AssetBinding, "field_key"),
    ],
)
def test_non_type_identifiers_remain_strict(model, field):
    with pytest.raises(ValidationError):
        model._meta.get_field(field).run_validators("blog-post")


def test_migration_state_matches_canonical_type_validators():
    migration = import_module("sitecontent.migrations.0042_public_pack_type_keys").Migration
    assert migration.dependencies == [("sitecontent", "0041_workspace_revision_tenant_scope")]
    for operation in migration.operations:
        model = {
            "contenttypedefinition": ContentTypeDefinition,
            "contentfielddefinition": ContentFieldDefinition,
            "contentrelationship": ContentRelationship,
            "assetbinding": AssetBinding,
        }[operation.model_name]
        assert operation.field.validators == model._meta.get_field(operation.name).validators
        valid = (
            VALID if operation.name in {"type_key", "target_type"} else ["old_type", "a_", "a" * 63]
        )
        invalid = (
            INVALID if operation.name in {"type_key", "target_type"} else INVALID + ["blog-post"]
        )
        for key in valid:
            operation.field.run_validators(key)
        for key in invalid:
            with pytest.raises(ValidationError):
                operation.field.run_validators(key)


@pytest.mark.django_db
@pytest.mark.parametrize("identifier", ["preset", "field"])
def test_native_full_clean_rejects_trailing_newline_in_strict_identifiers(identifier):
    definition = ContentTypeDefinition.objects.create(
        site_id="site-a", type_key="article", name="Article"
    )
    if identifier == "preset":
        instance = definition
        instance.preset_id = "article\n"
    else:
        instance = ContentFieldDefinition(
            definition=definition, field_key="title\n", label="Title", field_kind="short_text"
        )
    with pytest.raises(ValidationError):
        instance.full_clean()
