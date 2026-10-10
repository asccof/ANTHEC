# ANTHEEC

Independent institutional platform. Synthetic development only; production, real-person/clinical data, paid services and external delivery remain blocked.

## Current authority and scope

Owner-approved POL-01–08: [policy register](docs/APPROVED_POLICIES.md). These supersede conflicting historical proposals. Third-tier membership approval/renewal atomically grants linked annual professional accreditation and separate gold card/certificate. [Current contracts](docs/DOMAIN_CONTRACTS.md), [phased gaps](docs/POLICY_EXECUTION.md) and [execution evidence](docs/STATUS.md) distinguish tested services from full platform acceptance.

Implemented core: versioned prices/fixed quotes, verified cash/transfer, exemptions/refunds, membership/renewal, linked and independent accreditation decisions, encrypted printable documents/outbox, QR or reference+code verification, guardian consent/admission/capacity and unique attendance, primary/delegated directors and MFA. Finished end-user/admin forms, private assessment/upload workflow, optional directory, complete CMS translations/partners and legal/security/restore acceptance remain tracked in issues #5–10. Artifacts are development printable HTML, not production PDF templates.

## Local development (Python 3.12)

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py seed_policy_prices
python manage.py createsuperuser --username synthetic-primary --email primary@example.invalid
python manage.py bootstrap_authority synthetic-primary
```

Set `ANTHEEC_DATA_KEY` privately to a newly generated Fernet key (32 bytes, URL-safe base64), and retain it securely for this synthetic database. Do not commit or print it to logs. Missing key fails document issuance atomically; encryption rotation/backup recovery remains a readiness gate. Test settings supply an explicitly synthetic fixture key.

```sh
python manage.py runserver 127.0.0.1:8000
```

Open `/ar/`, `/fr/`, `/en/` and `/admin/`. The designated primary must enroll a TOTP authenticator at `/security/enroll/`, confirm password+factor, and save the displayed one-use recovery codes privately. Password+factor challenge is at `/security/challenge/`; sensitive commands require reauthentication within five minutes. Primary assignment cannot be changed through a web endpoint. Do not create operational directors as Django superusers: appoint/revoke them with the primary-only delegated command.

Business commands are JSON POSTs to `/operations/<action>/` with a unique `key`; allowed action/payload definitions are in `governance/services.py` and `governance/views.py`. They require authenticated, MFA-verified current primary/delegation and CSRF. This is a service/API increment, not finished application forms. Managed synthetic profiles and activities are test/development fixtures; enrollment UI remains pending. `/registrations/request/` accepts only the account's own profile or explicit guardian consent for its minor. `/verify/` exposes only allowlisted document fields after valid QR token or reference+code. `/my-documents/<id>/` permits holder/guardian or recently reauthenticated director. No public media/document filesystem route exists.

```sh
python manage.py render_policy_documents --limit 100
```

The local worker renders/retries encrypted printable jobs, preserving serials; it sends nothing externally. Production settings deliberately raise an error. Protected backups, archive/retention, private file scanning, complete recovery and independent security/legal review are prerequisites to real data.

## Validation

```sh
python tools/validate_baseline.py
python -m unittest discover -s tests -v
pip check
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test content governance --settings=antheec_app.settings.test
```

SQLite runs local acceptance tests; three concurrency tests intentionally require PostgreSQL. CI uses PostgreSQL 16. To test against a local instance set `ANTHEEC_DB_ENGINE=postgresql`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`, `PGHOST`, `PGPORT`. PostgreSQL evidence must come from actual CI, not SQLite. Original source attachments/private criteria are excluded from this public repository; source hashes preserve traceability. No MHIOS code or governance is imported.

## Institutional cards (owner-authorized Phase 1)

Protected AR/FR/EN administration: `/operations/institutional/`. Existing MFA-authorized directors grant recorded office terms or permanent free founder cards, record decisions and reissue documents. Institutional cards confer no platform privileges. See [Phase 1 contract and traceability](docs/INSTITUTIONAL_CARDS_PHASE1.md). Six concurrency tests now require PostgreSQL.
