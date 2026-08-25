from django.contrib import admin

from .models import (
    ContentRecord,
    ContentRevision,
    FormSubmission,
    FormDeliveryOutbox,
    MediaAsset,
    MediaVariant,
    RedirectRule,
    SearchDocument,
)

for model in (
    ContentRecord,
    ContentRevision,
    FormSubmission,
    FormDeliveryOutbox,
    MediaAsset,
    MediaVariant,
    RedirectRule,
    SearchDocument,
):
    admin.site.register(model)
