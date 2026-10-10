# ANTHEEC

Independent institutional platform. Development only: no production deployment, paid services, real-person data or clinical records.

## Local development (Python 3.12)

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8000
```

Use only synthetic accounts. Open `/ar/`, `/fr/`, `/en/`, and `/admin/`. Edit structured content with Wagtail, copy it into another locale using Simple Translation, manually translate, save a draft, preview, publish, and restore from revision history. External translation and email delivery are disabled. Separate reviewer enforcement, MFA, scheduled-publication acceptance and business workflows remain pending.

SQLite validates local CMS behavior. PostgreSQL 16 is configured in CI. To run against a local PostgreSQL instance set `ANTHEEC_DB_ENGINE=postgresql`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`, `PGHOST`, `PGPORT`. Production settings deliberately raise an error. No media/document serving route is exposed; this increment is for text content only.

## Validation

```sh
python -m unittest discover -s tests -v
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test content --settings=antheec_app.settings.test
```

Engineering basis: `docs/INCEPTION_AR.md`, `requirements/baseline.json`, `docs/DECISIONS.md`. Execution evidence: `docs/STATUS.md`. Original source attachments are excluded from the public repository. Source hashes preserve traceability. Issue #1 tracks this first increment.
