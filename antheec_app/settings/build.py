"""Static-only image build; no runtime secrets or database access."""
from .base import *  # noqa: F403
import os
from django.core.exceptions import ImproperlyConfigured
if os.environ.get("ANTHEEC_MODE", "development") != "development":
    raise ImproperlyConfigured("Static build settings cannot be used for owner testing.")
SECRET_KEY = "static-build-only-not-a-runtime-secret"
DEBUG = False
STORAGES = {
    "default": {"BACKEND": "governance.deployment.DisabledMediaStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
