from django.apps import AppConfig


class GovernanceConfig(AppConfig):
    name = "governance"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from . import login_sessions  # noqa: F401
