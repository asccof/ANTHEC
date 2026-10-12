"""Shared development/CI configuration. Production is deliberately unavailable."""
import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parents[2]
if os.environ.get("ANTHEEC_MODE", "development") not in {"development", "test"}:
    raise ImproperlyConfigured("Only development and test modes are authorized.")

INSTALLED_APPS = [
    "governance", "django_otp", "django_otp.plugins.otp_totp",
    "content", "wagtail.contrib.simple_translation", "wagtail.locales",
    "wagtail.contrib.redirects", "wagtail.sites", "wagtail.users",
    "wagtail.snippets", "wagtail.documents", "wagtail.images",
    "wagtail.search", "wagtail.admin", "wagtail", "modelcluster", "taggit",
    "django_filters", "django.contrib.admin", "django.contrib.auth",
    "django.contrib.contenttypes", "django.contrib.sessions",
    "django.contrib.messages", "django.contrib.staticfiles",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "governance.middleware.PolicyLocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "governance.middleware.AdminSecurityMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
]
ROOT_URLCONF = "antheec_app.urls"
WSGI_APPLICATION = "antheec_app.wsgi.application"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "antheec_app/templates"], "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
        "django.template.context_processors.i18n",
    ]},
}]
if os.environ.get("ANTHEEC_DB_ENGINE", "sqlite") == "postgresql":
    DATABASES = {"default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("PGDATABASE", "antheec_test"),
        "USER": os.environ.get("PGUSER", "antheec"),
        "PASSWORD": os.environ.get("PGPASSWORD", ""),
        "HOST": os.environ.get("PGHOST", "127.0.0.1"),
        "PORT": os.environ.get("PGPORT", "5432"),
    }}
elif os.environ.get("ANTHEEC_DB_ENGINE", "sqlite") == "sqlite":
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
else:
    raise ImproperlyConfigured("Unsupported database engine")

LANGUAGE_CODE = "ar"
LANGUAGES = [("ar", "العربية"), ("fr", "Français"), ("en", "English")]
WAGTAIL_I18N_ENABLED = True
WAGTAIL_CONTENT_LANGUAGES = LANGUAGES
TIME_ZONE = "Africa/Casablanca"
USE_I18N = True
USE_TZ = True
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "antheec_app/static"]
MEDIA_ROOT = BASE_DIR / "private_media"
MEDIA_URL = "/private-media/"
FILE_UPLOAD_PERMISSIONS = 0o600
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o700
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
WAGTAILDOCS_MAX_UPLOAD_SIZE = 10 * 1024 * 1024
WAGTAILDOCS_EXTENSIONS = ["pdf", "txt"]
WAGTAIL_SITE_NAME = "ANTHEEC"
WAGTAILADMIN_BASE_URL = "http://127.0.0.1:8000"
WAGTAILSEARCH_BACKENDS = {"default": {"BACKEND": "wagtail.search.backends.database"}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

ANTHEEC_DATA_KEY = os.environ.get("ANTHEEC_DATA_KEY", "")
OTP_TOTP_ISSUER = "ANTHEEC development"
OTP_TOTP_THROTTLE_FACTOR = 1
SESSION_COOKIE_AGE = 3600

ANTHEEC_PUBLIC_ORIGIN = "http://127.0.0.1:8000" # local synthetic documents only

# Approved identity is supplied privately, not committed as actual person data.
import json as _signatory_json
try:
    ANTHEEC_CERTIFICATE_SIGNATORY = _signatory_json.loads(os.environ["ANTHEEC_CERTIFICATE_SIGNATORY_JSON"]) if os.environ.get("ANTHEEC_CERTIFICATE_SIGNATORY_JSON") else None
except (ValueError, TypeError) as exc:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("Invalid private certificate signatory configuration") from exc
