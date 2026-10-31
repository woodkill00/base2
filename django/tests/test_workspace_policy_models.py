"""Canonical shared policy and review storage invariants."""

import uuid

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from common import models as canonical
from sitecontent.models import (
    ContentRecord,
    ReviewApproval,
    ReviewDigestBatch,
    ReviewNotificationDelivery,
    ReviewNotificationIntent,
    ReviewSubject,
    WorkspacePolicy,
)

pytestmark = pytest.mark.django_db


def record(site="site-one", slug="reviewed"):
    return ContentRecord.objects.create(
        site_id=site, content_type="page", slug=slug, title="Review"
    )


def test_every_new_domain_begins_in_common_and_uses_explicit_tenant_scope():
    for model in [
        WorkspacePolicy,
        ReviewSubject,
        ReviewApproval,
        ReviewDigestBatch,
        ReviewNotificationIntent,
        ReviewNotificationDelivery,
    ]:
        primitive = getattr(canonical, model.__name__)
        assert primitive._meta.abstract
        assert issubclass(model, primitive)
        assert model._meta.get_field("site_id").max_length == 63


def test_policy_defaults_fail_closed_and_has_one_revision_per_site():
    policy = WorkspacePolicy.objects.create(site_id="site-one")
    assert policy.require_review and policy.public_access == "members_only"
    assert policy.schema_version == policy.version == 1
    assert policy.provenance == "default" and policy.organization_id is None
    with pytest.raises(IntegrityError), transaction.atomic():
        WorkspacePolicy.objects.create(site_id="site-one")
    WorkspacePolicy.objects.create(site_id="site-two")


@pytest.mark.parametrize(
    "values",
    [
        {"schema_version": 2},
        {"version": 0},
        {"public_access": "everyone"},
        {"provenance": "guessed"},
    ],
)
def test_policy_closed_database_contract(values):
    with pytest.raises(IntegrityError), transaction.atomic():
        WorkspacePolicy.objects.create(site_id="site-one", **values)


def test_subject_unknown_provenance_requires_explicit_adoption_and_independent_reviewer():
    creator, editor, submitter, reviewer = (uuid.uuid4() for _ in range(4))
    subject = ReviewSubject.objects.create(
        site_id="site-one", record=record(), fingerprint="a" * 64
    )
    with pytest.raises(ValidationError, match="review_provenance_unresolved"):
        subject.validate_reviewer(reviewer)
    subject.semantic_author_id = editor
    subject.submitter_id = submitter
    with pytest.raises(ValidationError, match="review_provenance_unresolved"):
        subject.validate_reviewer(reviewer)
    subject.adopted_snapshot = True
    subject.validate_reviewer(reviewer)
    subject.original_creator_id = creator
    for actor in [creator, editor, submitter]:
        with pytest.raises(ValidationError, match="independent_reviewer_required"):
            subject.validate_reviewer(actor)


def test_record_scope_checks_and_single_subject():
    content = record()
    with pytest.raises(ValidationError, match="review_record_scope_invalid"):
        ReviewSubject(site_id="site-two", record=content, fingerprint="a" * 64).full_clean()
    ReviewSubject.objects.create(site_id="site-one", record=content, fingerprint="a" * 64)
    with pytest.raises(IntegrityError), transaction.atomic():
        ReviewSubject.objects.create(site_id="site-one", record=content, fingerprint="a" * 64)


def test_approval_is_append_only_and_revision_bound():
    content = record()
    approval = ReviewApproval.objects.create(
        site_id="site-one",
        record=content,
        subject_revision=uuid.uuid4(),
        fingerprint="a" * 64,
        policy_version=1,
        reviewer_id=uuid.uuid4(),
    )
    with pytest.raises(ValidationError, match="review_approval_append_only"):
        approval.save()
    with pytest.raises(ValidationError, match="review_approval_append_only"):
        approval.delete()
    with pytest.raises(ValidationError, match="review_approval_append_only"):
        ReviewApproval.objects.filter(pk=approval.pk).update(policy_version=2)
    with pytest.raises(ValidationError, match="review_approval_append_only"):
        ReviewApproval.objects.filter(pk=approval.pk).delete()


def test_intent_and_digest_and_sink_effects_are_unique():
    content, recipient, submission = record(), uuid.uuid4(), uuid.uuid4()
    values = dict(
        site_id="site-one",
        record=content,
        submission_id=submission,
        subject_revision=uuid.uuid4(),
        recipient_id=recipient,
    )
    intent = ReviewNotificationIntent.objects.create(**values)
    with pytest.raises(IntegrityError), transaction.atomic():
        ReviewNotificationIntent.objects.create(**values)
    batch_values = dict(
        site_id="site-one", recipient_id=recipient, digest_date=timezone.now().date()
    )
    batch = ReviewDigestBatch.objects.create(**batch_values)
    with pytest.raises(IntegrityError), transaction.atomic():
        ReviewDigestBatch.objects.create(**batch_values)
    ReviewNotificationDelivery.objects.create(
        site_id="site-one",
        effect_key="immediate:" + str(intent.id),
        recipient_id=recipient,
        intent=intent,
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        ReviewNotificationDelivery.objects.create(
            site_id="site-one",
            effect_key="immediate:" + str(intent.id),
            recipient_id=recipient,
            intent=intent,
        )
    with pytest.raises(ValidationError, match="review_delivery_source_invalid"):
        ReviewNotificationDelivery(
            site_id="site-one",
            effect_key="both",
            recipient_id=recipient,
            intent=intent,
            digest_batch=batch,
        ).full_clean()


def test_review_choices_and_attempts_are_database_bounded():
    values = dict(
        site_id="site-one",
        record=record(),
        submission_id=uuid.uuid4(),
        subject_revision=uuid.uuid4(),
        recipient_id=uuid.uuid4(),
    )
    for invalid in [
        {"channel": "browser"},
        {"status": "unknown"},
        {"attempts": 9},
        {"event": "arbitrary"},
    ]:
        with pytest.raises(IntegrityError), transaction.atomic():
            ReviewNotificationIntent.objects.create(**values, **invalid)


@pytest.mark.parametrize("site", ["a", "1", "a-b", "a" * 63])
def test_policy_accepts_existing_runtime_tenant_identifiers(site):
    policy = WorkspacePolicy(site_id=site)
    policy.full_clean()
    policy.save()
    assert WorkspacePolicy.objects.for_tenant(site).get().pk == policy.pk


@pytest.mark.parametrize("site", ["", "A", "a_b", "a" * 64, "a/b"])
def test_policy_database_rejects_noncanonical_scope(site):
    with pytest.raises(IntegrityError), transaction.atomic():
        WorkspacePolicy.objects.create(site_id=site)


@pytest.mark.parametrize(
    "values",
    [
        {"fingerprint": "not-a-hash"},
        {"semantic_generation": 0},
        {"schema_version": 2},
        {"schedule_policy_version": 0},
    ],
)
def test_subject_database_rejects_invalid_revision_contract(values):
    fields = {"fingerprint": "a" * 64, **values}
    with pytest.raises(IntegrityError), transaction.atomic():
        ReviewSubject.objects.create(site_id="site-one", record=record(), **fields)


def test_intent_and_delivery_validate_tenant_and_recipient_scope():
    content = record()
    recipient = uuid.uuid4()
    batch = ReviewDigestBatch.objects.create(
        site_id="site-one", recipient_id=recipient, digest_date=timezone.now().date()
    )
    intent = ReviewNotificationIntent(
        site_id="site-one",
        record=content,
        submission_id=uuid.uuid4(),
        subject_revision=uuid.uuid4(),
        recipient_id=recipient,
        digest_batch=batch,
    )
    intent.full_clean()
    intent.save()
    intent.recipient_id = uuid.uuid4()
    with pytest.raises(ValidationError, match="review_digest_scope_invalid"):
        intent.full_clean()
    intent.recipient_id = recipient
    delivery = ReviewNotificationDelivery(
        site_id="site-one",
        recipient_id=recipient,
        effect_key="digest:" + str(batch.id),
        digest_batch=batch,
    )
    delivery.full_clean()
    delivery.recipient_id = uuid.uuid4()
    with pytest.raises(ValidationError, match="review_delivery_scope_invalid"):
        delivery.full_clean()
    delivery.recipient_id = recipient
    delivery.site_id = "site-two"
    with pytest.raises(ValidationError, match="review_delivery_scope_invalid"):
        delivery.full_clean()
    immediate = ReviewNotificationDelivery(
        site_id="site-one",
        recipient_id=recipient,
        effect_key="immediate:" + str(intent.id),
        intent=intent,
    )
    immediate.full_clean()


def test_policy_query_rejects_invalid_tenant():
    with pytest.raises(ValidationError, match="tenant_invalid"):
        WorkspacePolicy.objects.for_tenant("UPPER")


def test_reconstructed_approval_cannot_overwrite_existing_uuid():
    values = dict(
        site_id="site-one",
        record=record(),
        subject_revision=uuid.uuid4(),
        fingerprint="a" * 64,
        policy_version=1,
        reviewer_id=uuid.uuid4(),
    )
    approval = ReviewApproval.objects.create(**values)
    with pytest.raises(IntegrityError), transaction.atomic():
        ReviewApproval(id=approval.id, **{**values, "policy_version": 2}).save()
    with pytest.raises(ValidationError, match="review_approval_append_only"):
        ReviewApproval(**values).save(force_update=True)
    approval.refresh_from_db()
    assert approval.policy_version == 1
