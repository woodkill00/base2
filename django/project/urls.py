from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("internal/users/", include("users.urls")),
    path("internal/catalog/", include("catalog.urls")),
]
