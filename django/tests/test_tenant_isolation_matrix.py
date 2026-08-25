from __future__ import annotations

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import RequestFactory, TestCase
from django.utils import timezone

from sitecontent.models import ContentRecord, SearchDocument
from users.models import Membership, Organization


class TenantIsolationMatrixTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        user_model = get_user_model()
        self.user_a = user_model.objects.create_user(username="tenant-a-admin")
        self.user_b = user_model.objects.create_user(username="tenant-b-admin")
        self.user_a.is_staff = True
        self.user_a.save(update_fields=["is_staff"])
        self.user_a.user_permissions.add(
            Permission.objects.get(codename="view_contentrecord")
        )
        self.org_a = Organization.objects.create(name="Tenant A", slug="tenant-a")
        self.org_b = Organization.objects.create(name="Tenant B", slug="tenant-b")
        Membership.objects.create(
            organization=self.org_a,
            user=self.user_a,
            role=Membership.Role.ADMIN,
            status=Membership.Status.ACTIVE,
        )
        Membership.objects.create(
            organization=self.org_b,
            user=self.user_b,
            role=Membership.Role.ADMIN,
            status=Membership.Status.ACTIVE,
        )
        self.a = ContentRecord.objects.create(
            site_id="tenant-a", content_type="page", slug="a", title="A"
        )
        self.b = ContentRecord.objects.create(
            site_id="tenant-b", content_type="page", slug="b", title="B"
        )

    def test_tenant_queryset_requires_canonical_id_and_never_crosses_scope(self):
        self.assertEqual(list(ContentRecord.objects.for_tenant("tenant-a")), [self.a])
        with self.assertRaisesMessage(ValidationError, "tenant_invalid"):
            ContentRecord.objects.for_tenant("../tenant")

    def test_search_document_rejects_cross_tenant_content(self):
        document = SearchDocument(
            site_id="tenant-b",
            content=self.a,
            title="Cross tenant",
            body="private",
            url_path="/cross",
            source_updated_at=timezone.now(),
        )
        with self.assertRaises(ValidationError):
            document.full_clean()

    def test_admin_queryset_and_object_permissions_are_membership_scoped(self):
        request = self.factory.get("/admin/sitecontent/contentrecord/")
        request.user = self.user_a
        model_admin = admin.site._registry[ContentRecord]
        self.assertEqual(list(model_admin.get_queryset(request)), [self.a])
        self.assertTrue(model_admin.has_view_permission(request, self.a))
        self.assertFalse(model_admin.has_view_permission(request, self.b))
        self.assertFalse(model_admin.has_change_permission(request, self.b))
        self.assertFalse(model_admin.has_delete_permission(request, self.b))
        with self.assertRaisesMessage(PermissionDenied, "cross_tenant_forbidden"):
            model_admin.save_model(request, self.b, form=None, change=True)

    def test_superuser_retains_explicit_operator_scope(self):
        user_model = get_user_model()
        operator = user_model.objects.create_superuser(
            username="operator", email="operator@example.test", password="test-only-password"
        )
        request = self.factory.get("/admin/sitecontent/contentrecord/")
        request.user = operator
        model_admin = admin.site._registry[ContentRecord]
        self.assertEqual(set(model_admin.get_queryset(request)), {self.a, self.b})
        self.assertTrue(model_admin.has_change_permission(request, self.b))
