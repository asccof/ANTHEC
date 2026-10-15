# ANTHEC

Independent association platform, currently a **private owner-only synthetic trial**. Current completion evidence: [readiness review](docs/RELEASE_READINESS_REVIEW.md), [completeness register](docs/COMPLETENESS_REVIEW.md) and [execution history](docs/STATUS.md). Owner-approved [POL-01–08](docs/APPROVED_POLICIES.md) remain authoritative. Legacy internal package names use ANTHEEC; the current displayed acronym is ANTHEC.

## Current behavior and boundaries

The owner has accepted enabled membership/review screens, institutional/honorary designation screens, partnership review, independent assessment, activity/request review, director/pricing screens and AR/FR/EN presentation. This is **not** acceptance of the disabled financial/issuance/attendance path on hosting, real data, final editorial/legal content or a public launch.

Implemented services include append-only prospective prices/fixed quotes, verified cash/transfer, exemptions/refund decisions, membership/renewal, linked third-tier professional accreditation, independent assessments, institutional roles, authority/delegation/MFA/revocation, guardian consent/admission/capacity/attendance and controlled partner visibility. Independent criteria/notes/fees remain private. Assessment and partnership do not implicitly grant membership or administrative authority.

The document system includes approved artwork and protected encrypted card/certificate PDF artifacts with immutable photo/signature/stamp snapshots, reference/QR/additional-code verification, replacement history and status propagation. Raster signing assets are not a PKI digital signature. Invitation output still has an Arabic HTML fallback; complete FR/EN invitation output is a recorded gap. Participation certificates remain NOT ISSUED design proofs. See [premium documents](docs/PREMIUM_DOCUMENTS.md) and [readiness matrix](docs/RELEASE_READINESS_REVIEW.md).

On the deployed owner-testing service, only the verified active primary sees dynamic data. Registration/applications/renewal, payment/refund execution, document issuance/PDF generation/outbox processing, official verification and external delivery remain blocked. Settings reject public production mode. No new paid resource, plan change, real-person/clinical data, external delivery, DNS change or Tighri modification is implied by this repository or current review.

## Operational entry points

Log in at `/admin/login/`, complete password + authenticator verification, then use the administrative menu or return-to-site navigation. Sensitive writes require recent reauthentication at `/security/challenge/` (five minutes). Never send credentials, TOTP secrets, recovery codes or signing assets in chat or commit them.

| Path | Access / purpose |
|---|---|
| `/ar/`, `/fr/`, `/en/` | Owner-only trial presentation; existing manual CMS revisions/translations preserved |
| `/operations/membership/` | Membership review and finance/rights controls, with live trial guards |
| `/operations/institutional/` | Recorded office terms and free permanent founder/honorary designations |
| `/operations/accreditation/` | Private independent casework; annual effective dates derive from final approval, course dates remain explicit |
| `/operations/activities/` | Configuration, admission, guardian evidence and invitation-based attendance controls |
| `/operations/partners/` | Proposal review and hidden/localized partner records |
| `/operations/directors/` | Primary-only delegation management; the primary cannot be replaced here |
| `/operations/pricing/` | Prospective membership price versions, fixed prior quotes |
| `/operations/portraits/`, `/operations/certificate-assets/` | Restricted immutable issuance assets; protected synthetic testing only |
| `/members/`, `/my-documents/`, `/verify/` | Isolated-test member/document/verification paths; their protected live actions remain disabled |

Optional `seed_partner_demo`, `seed_accreditation_demo`, `seed_activity_demo` and `seed_operations_demo` commands are idempotent **owner-testing-only** fixtures invoked manually, never automatic deployment hooks. They do not approve rights, issue documents, collect funds or send credentials. The operations fixture creates only an unusable-password, unprivileged synthetic candidate.

## Local synthetic development (Python 3.12)

Use a separate development database and an `example.invalid` identity. Never load a deployed database or real records into development. Install exact pinned dependencies and supply a newly generated private `ANTHEEC_DATA_KEY` through secure local configuration; retain it separately from any export. Test settings already contain a clearly synthetic key for disposable test databases.

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate --settings=antheec_app.settings.dev
python manage.py seed_demo --settings=antheec_app.settings.dev
python manage.py seed_policy_prices --settings=antheec_app.settings.dev
python manage.py createsuperuser --username synthetic-primary --email primary@example.invalid --settings=antheec_app.settings.dev
python manage.py bootstrap_authority synthetic-primary --settings=antheec_app.settings.dev
python manage.py runserver 127.0.0.1:8000 --settings=antheec_app.settings.dev
```

Business commands remain CSRF-protected JSON POSTs at `/operations/<action>/` as well as bounded forms. Current authority, confirmed MFA, epoch and recent reauthentication are enforced in the service boundary; unrelated Django permissions do not establish authority. Do not create delegates as superusers. Synthetic fixtures do not replace identity verification or recovery procedures for real operations.

## Validation and readiness

```sh
python tools/validate_baseline.py
python -m unittest discover -s tests -v
pip check
python manage.py check --settings=antheec_app.settings.test
python manage.py makemigrations --check --dry-run --settings=antheec_app.settings.test
python manage.py test content governance --settings=antheec_app.settings.test
```

Local SQLite is not PostgreSQL lock evidence. CI runs the full suite on disposable PostgreSQL 16, metadata/system/drift/dependency checks, container/runtime validation and authenticated synthetic export/restore/decryption in a distinct database. Exact-head CI/review and tested-tree verification precede authorized merges/private deploys.

[Release readiness](docs/RELEASE_READINESS_REVIEW.md) separates implemented and owner-accepted trial behavior from real hosted issuance/restore/key/capacity evidence, optional scope, final content and independent legal/privacy/security gates. Existing memory observations do not prove the historical OOM allocation root cause fixed. Historical preparation documents remain traceable but do not override the current evidence register or owner authorization. Original private source attachments and detailed criteria are excluded; hashes preserve traceability. No MHIOS code or governance is imported.


[Owner acceptance scenarios (Arabic)](docs/OWNER_ACCEPTANCE_AR.md) and [recovery/security procedure (Arabic)](docs/RECOVERY_SECURITY_RUNBOOK_AR.md) are the execution package. After the package is reviewed and privately deployed, `python manage.py check_owner_readiness` in the ANTHEC shell reports sanitized read-only observations only; it does not prove key custody, restore success or launch readiness. Keep database external access closed. Never run CI recovery/test settings against the hosted database.
