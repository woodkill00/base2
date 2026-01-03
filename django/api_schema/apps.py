from django.apps import AppConfig


class ApiSchemaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api_schema"
    verbose_name = "API Schema (FastAPI tables)"
