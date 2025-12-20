from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CommonConfig(AppConfig):
    name = "common"
    verbose_name = _("Common")

    def ready(self):
        try:
            import common.signals  # noqa: F401
        except ImportError:
            # Signals are optional
            pass