"""Offline image smoke check with ephemeral synthetic settings, never live data."""
import json
import os
import secrets
import sys
from pathlib import Path
from cryptography.fernet import Fernet

if os.geteuid() != 10001 or os.getegid() != 10001:
    raise RuntimeError("Container smoke check requires the non-root runtime user.")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Generated inside the disposable, network-disabled CI container. Never print
# values or use this utility to configure an actual deployment.
os.environ.update({
    "DJANGO_SETTINGS_MODULE": "antheec_app.settings.production",
    "ANTHEEC_MODE": "owner-testing",
    "ANTHEEC_SECRET_KEY": secrets.token_urlsafe(64),
    "ANTHEEC_DATA_KEY": Fernet.generate_key().decode(),
    "ANTHEEC_PUBLIC_ORIGIN": "https://synthetic.example.invalid",
    "DATABASE_URL": "postgresql://synthetic:synthetic@localhost/anthec_owner_testing",
})

import django
django.setup()
from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.checks import run_checks

assert not settings.DEBUG and settings.ANTHEEC_OWNER_TESTING
with staticfiles_storage.open("staticfiles.json") as manifest:
    paths = json.load(manifest)["paths"]
assert paths, "Collected static manifest is empty."
for original, hashed in paths.items():
    assert staticfiles_storage.url(original).endswith(hashed)
    with staticfiles_storage.open(hashed) as asset:
        asset.read(1)
issues = run_checks(include_deployment_checks=True)
assert {issue.id for issue in issues} == {"security.W005", "security.W021"}
print("PASS: non-root production startup, static manifest/assets and deployment checks; offline synthetic only.")
