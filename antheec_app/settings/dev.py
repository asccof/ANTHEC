import os
import secrets
from .base import *  # noqa: F403
from django.core.exceptions import ImproperlyConfigured

if os.environ.get("ANTHEEC_MODE") == "owner-testing":
    raise ImproperlyConfigured("Owner testing requires the secure production settings module.")

DEBUG = True
# Ephemeral local key; export ANTHEEC_SECRET_KEY to keep local sessions across restarts.
SECRET_KEY = os.environ.get("ANTHEEC_SECRET_KEY") or secrets.token_urlsafe(64)
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]
