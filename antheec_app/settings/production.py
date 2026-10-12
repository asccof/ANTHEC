"""Render owner-only testing. Public production and issuance remain unavailable."""
import os
import re
import base64
import hmac
from urllib.parse import urlsplit, unquote
from cryptography.fernet import Fernet
from django.core.exceptions import ImproperlyConfigured
from .base import *  # noqa: F403


def required(name):
    value = os.environ.get(name, "")
    if not value:
        raise ImproperlyConfigured(f"{name} is required; set it privately in Render.")
    return value


if os.environ.get("ANTHEEC_MODE") != "owner-testing":
    raise ImproperlyConfigured("Only explicit owner-testing deployment is authorized.")
DEBUG = False
ANTHEEC_OWNER_TESTING = True
SECRET_KEY = required("ANTHEEC_SECRET_KEY")
if len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 5:
    raise ImproperlyConfigured("A unique random secret of at least 50 characters is required.")
ANTHEEC_DATA_KEY = required("ANTHEEC_DATA_KEY")
try:
    Fernet(ANTHEEC_DATA_KEY.encode())
except (ValueError, TypeError) as exc:
    raise ImproperlyConfigured("A valid private Fernet data key is required.") from exc
if hmac.compare_digest(
        base64.urlsafe_b64decode(ANTHEEC_DATA_KEY.encode()),
        base64.urlsafe_b64decode(b"MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")):
    raise ImproperlyConfigured("The repository test key must never be deployed.")

origin = urlsplit(required("ANTHEEC_PUBLIC_ORIGIN"))
if (origin.scheme != "https" or origin.path not in {"", "/"} or origin.query or
        origin.fragment or origin.username or origin.password or not origin.hostname or
        not re.fullmatch(r"[a-z0-9]+(?:[a-z0-9.-]*[a-z0-9])?", origin.netloc)):
    raise ImproperlyConfigured("One exact HTTPS hostname is required; no wildcard, port or URL path.")
ANTHEEC_PUBLIC_ORIGIN = "https://" + origin.hostname
ALLOWED_HOSTS = [origin.hostname]
CSRF_TRUSTED_ORIGINS = [ANTHEEC_PUBLIC_ORIGIN]
WAGTAILADMIN_BASE_URL = ANTHEEC_PUBLIC_ORIGIN
WAGTAIL_SITE_NAME = "ANTHEC — private owner testing"
OTP_TOTP_ISSUER = "ANTHEC owner testing"

database = urlsplit(required("DATABASE_URL"))
if (database.scheme not in {"postgres", "postgresql"} or not database.hostname or
        not database.username or not database.password or database.query or database.fragment or
        database.path != "/anthec_owner_testing"):
    raise ImproperlyConfigured("A dedicated anthec_owner_testing PostgreSQL database URL is required.")
try:
    database_port = database.port or 5432
except ValueError as exc:
    raise ImproperlyConfigured("Invalid PostgreSQL port.") from exc
DATABASES = {"default": {
    "ENGINE": "django.db.backends.postgresql", "NAME": "anthec_owner_testing",
    "USER": unquote(database.username), "PASSWORD": unquote(database.password),
    "HOST": database.hostname, "PORT": database_port, "CONN_MAX_AGE": 60,
    "CONN_HEALTH_CHECKS": True,
    "OPTIONS": {"sslmode": "require", "connect_timeout": 10},
}}
# Only trust this header behind Render's TLS ingress, never an exposed container.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SECURE_REDIRECT_EXEMPT = [r"^health/$"]
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 3600  # staged; no subdomain/preload commitment
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_REFERRER_POLICY = "no-referrer"
EMAIL_BACKEND = "django.core.mail.backends.dummy.EmailBackend"
MIDDLEWARE = list(MIDDLEWARE)  # noqa: F405
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
MIDDLEWARE.insert(MIDDLEWARE.index("governance.middleware.AdminSecurityMiddleware"),
                  "governance.deployment.OwnerTestingMiddleware")
STORAGES = {
    # Encrypted database assets retain their existing protected approval flows.
    # No filesystem uploads before private storage and its restore are approved.
    "default": {"BACKEND": "governance.deployment.DisabledMediaStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
WHITENOISE_AUTOREFRESH = False
WHITENOISE_USE_FINDERS = False
LOGGING = {
    "version": 1, "disable_existing_loggers": False,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "loggers": {"django.request": {"handlers": ["null"], "propagate": False},
                "django.security": {"handlers": ["null"], "propagate": False}},
}
