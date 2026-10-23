"""Secure hosted modes; operational activation requires a separate release decision."""
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


mode = os.environ.get("ANTHEEC_MODE")
if mode not in {"owner-testing", "public-preview", "operational"}:
    raise ImproperlyConfigured("Unsupported hosted mode.")
DEBUG = False
ANTHEEC_OWNER_TESTING = mode == "owner-testing"
ANTHEEC_PUBLIC_PREVIEW = mode == "public-preview"
ANTHEEC_OPERATIONAL = mode == "operational"
privacy_flag = os.environ.get('ANTHEEC_PRIVACY_NOTICE_ENABLED', '0')
if privacy_flag not in {'0', '1'} or (privacy_flag == '1' and not ANTHEEC_OPERATIONAL):
    raise ImproperlyConfigured('Privacy notice activation requires operational mode and an explicit 0/1 flag.')
ANTHEEC_PRIVACY_NOTICE_ENABLED = privacy_flag == '1'
ANTHEEC_PRIVACY_NOTICE_PUBLISHED_ON = os.environ.get('ANTHEEC_PRIVACY_NOTICE_PUBLISHED_ON', '')
if ANTHEEC_PRIVACY_NOTICE_ENABLED:
    from datetime import date as _privacy_date
    from datetime import datetime as _privacy_datetime
    from zoneinfo import ZoneInfo as _PrivacyZoneInfo
    try:
        _publication_day = _privacy_date.fromisoformat(ANTHEEC_PRIVACY_NOTICE_PUBLISHED_ON)
        if _publication_day > _privacy_datetime.now(_PrivacyZoneInfo(TIME_ZONE)).date():
            raise ValueError
        if _privacy_date.fromisoformat(ANTHEEC_PRIVACY_NOTICE_PUBLISHED_ON).isoformat() != ANTHEEC_PRIVACY_NOTICE_PUBLISHED_ON:
            raise ValueError
    except ValueError:
        raise ImproperlyConfigured('Privacy notice needs its actual ISO publication date.') from None
# No new mode is activated by deployment alone. This is an operator release
# acknowledgement, not evidence of legal acceptance or successful recovery.
if ANTHEEC_OPERATIONAL and os.environ.get("ANTHEEC_OPERATIONAL_RELEASE_APPROVED") != "1":
    raise ImproperlyConfigured("Operational mode requires a distinct approved release decision.")
for name in ("ANTHEEC_APPLICATIONS_ENABLED", "ANTHEEC_PAYMENTS_ENABLED", "ANTHEEC_ISSUANCE_ENABLED"):
    value = os.environ.get(name, "0")
    if value not in {"0", "1"} or (not ANTHEEC_OPERATIONAL and value != "0"):
        raise ImproperlyConfigured(f"{name} must be 0 in preview modes or exactly 0/1 in operational mode.")
    globals()[name] = value == "1"
if (ANTHEEC_PUBLIC_PREVIEW or ANTHEEC_OPERATIONAL) and os.environ.get("ANTHEEC_PUBLIC_CONTENT_APPROVED") != "1":
    raise ImproperlyConfigured("Review public CMS, activities and partners before exposing them.")
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

def exact_origin(value):
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or parsed.path not in {"", "/"} or parsed.query or
            parsed.fragment or parsed.username or parsed.password or not parsed.hostname or
            not re.fullmatch(r"[a-z0-9]+(?:[a-z0-9.-]*[a-z0-9])?", parsed.netloc)):
        raise ImproperlyConfigured("One exact HTTPS hostname is required; no wildcard, port or URL path.")
    return "https://" + parsed.hostname


ANTHEEC_PUBLIC_ORIGIN = exact_origin(required("ANTHEEC_PUBLIC_ORIGIN"))
ALLOWED_HOSTS = [urlsplit(ANTHEEC_PUBLIC_ORIGIN).hostname]
ANTHEEC_LEGACY_ORIGIN = os.environ.get("ANTHEEC_LEGACY_ORIGIN", "")
if ANTHEEC_LEGACY_ORIGIN:
    ANTHEEC_LEGACY_ORIGIN = exact_origin(ANTHEEC_LEGACY_ORIGIN)
    if not ANTHEEC_OPERATIONAL or ANTHEEC_LEGACY_ORIGIN == ANTHEEC_PUBLIC_ORIGIN:
        raise ImproperlyConfigured("Legacy redirects require operational mode and a distinct exact origin.")
    ALLOWED_HOSTS.append(urlsplit(ANTHEEC_LEGACY_ORIGIN).hostname)
CSRF_TRUSTED_ORIGINS = [ANTHEEC_PUBLIC_ORIGIN]
WAGTAILADMIN_BASE_URL = ANTHEEC_PUBLIC_ORIGIN
for _flag in ("ANTHEEC_SYNC_SITE_ORIGIN", "ANTHEEC_PUBLIC_DISCOVERY_ENABLED"):
    _value = os.environ.get(_flag, "0")
    if _value not in {"0", "1"} or (_value == "1" and not ANTHEEC_OPERATIONAL):
        raise ImproperlyConfigured(f"{_flag} requires operational mode and an explicit 0/1 flag.")
    globals()[_flag] = _value == "1"
WAGTAIL_SITE_NAME = "ANTHEC — private owner testing" if ANTHEEC_OWNER_TESTING else ("ANTHEC" if ANTHEEC_OPERATIONAL else "ANTHEC — preview")
OTP_TOTP_ISSUER = "ANTHEC" if ANTHEEC_OPERATIONAL else "ANTHEC owner testing"

database = urlsplit(required("DATABASE_URL"))
database_name = unquote(database.path.removeprefix("/"))
if (database.scheme not in {"postgres", "postgresql"} or not database.hostname or
        not database.username or not database.password or database.query or database.fragment or
        not re.fullmatch(r"anthec_owner_testing(?:_[a-z0-9]+)?", database_name)):
    raise ImproperlyConfigured("A dedicated anthec_owner_testing PostgreSQL database URL, optionally Render-suffixed, is required.")
try:
    database_port = database.port or 5432
except ValueError as exc:
    raise ImproperlyConfigured("Invalid PostgreSQL port.") from exc
DATABASES = {"default": {
    "ENGINE": "django.db.backends.postgresql", "NAME": database_name,
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
# Same-origin HTTPS form submissions need a non-opaque Origin/Referer for CSRF.
# Suppress referrers to other origins while preserving same-origin validation.
SECURE_REFERRER_POLICY = "same-origin"
EMAIL_BACKEND = "django.core.mail.backends.dummy.EmailBackend"
MIDDLEWARE = list(MIDDLEWARE)  # noqa: F405
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
MIDDLEWARE.insert(0, "governance.deployment.CanonicalOriginMiddleware")
MIDDLEWARE.insert(MIDDLEWARE.index("governance.middleware.AdminSecurityMiddleware"),
                  "governance.deployment.OwnerTestingMiddleware" if ANTHEEC_OWNER_TESTING
                  else ("governance.deployment.OperationalMiddleware" if ANTHEEC_OPERATIONAL
                        else "governance.deployment.PublicPreviewMiddleware"))
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
