from .dev import *  # noqa: F403

DEBUG = False
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

ANTHEEC_DATA_KEY = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="

ANTHEEC_CERTIFICATE_SIGNATORY = {"ar_name": "رئيس تجريبي", "latin_name": "Synthetic President", "capacity": "president"}
