import os
import secrets
from .base import *  # noqa: F403

DEBUG = True
# Ephemeral local key; export ANTHEEC_SECRET_KEY to keep local sessions across restarts.
SECRET_KEY = os.environ.get("ANTHEEC_SECRET_KEY") or secrets.token_urlsafe(64)
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]
