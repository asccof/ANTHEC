# ANTHEC

Independent association platform, currently a **private owner-only synthetic trial**. Current completion evidence: [readiness review](docs/RELEASE_READINESS_REVIEW.md), [completeness register](docs/COMPLETENESS_REVIEW.md) and [execution history](docs/STATUS.md). Owner-approved [POL-01–08](docs/APPROVED_POLICIES.md) remain authoritative. Legacy internal package names use ANTHEEC; the current displayed acronym is ANTHEC.

## Current behavior and boundaries

The owner has accepted enabled membership/review screens, institutional/honorary designation screens, partnership review, independent assessment, activity/request review, director/pricing screens and AR/FR/EN presentation. This is **not** acceptance of the disabled financial/issuance/attendance path on hosting, real data, final editorial/legal content or a public launch.

Implemented services include append-only prospective prices/fixed quotes, verified cash/transfer, exemptions/refund decisions, membership/renewal, linked third-tier professional accreditation, independent assessments, institutional roles, authority/delegation/MFA/revocation, guardian consent/admission/capacity/attendance and controlled partner visibility. Independent criteria/notes/fees remain private. Assessment and partnership do not implicitly grant membership or administrative authority.

The document system includes approved artwork and protected encrypted card/certificate PDF artifacts with immutable photo/signature/stamp snapshots, reference/QR/additional-code verification, replacement history and status propagation. Raster signing assets are not a PKI digital signature. Invitation output still has an Arabic HTML fallback; complete FR/EN invitation output is a recorded gap. Participation certificates remain NOT ISSUED design proofs. See [premium documents](docs/PREMIUM_DOCUMENTS.md) and [readiness matrix](docs/RELEASE_READINESS_REVIEW.md).

On the deployed owner-testing service, only the verified active primary sees dynamic data. Registration/applications/renewal, payment/refund execution, document issuance/PDF generation/outbox processing, official verification and external delivery remain blocked. Settings reject public production mode. No new paid resource, plan change, real-person/clinical data, external delivery, DNS change or Tighri modification is implied by this repository or current review.

## Operational entry points

The primary logs in at `/admin/login/` and completes authenticator verification once for that login. Delegates in isolated development/testing sign in with their own password at `/members/login/` and enter `/operations/workspace/`; current scoped sessions also have an Administrative workspace navigation link. No administrative OTP is required from delegates, and no repeated challenge or five-minute timer applies during the same login session. A new primary login after logout/expiry requires its factor again. Changed/revoked grants require a fresh delegated login. The hosted owner-testing gate remains primary-only. Never send credentials, TOTP secrets, recovery codes or signing assets in chat or commit them.

| Path | Access / purpose |
|---|---|
| `/ar/`, `/fr/`, `/en/` | Owner-only trial presentation; existing manual CMS revisions/translations preserved |
| `/operations/workspace/` | Current authenticated administrative session; links limited to explicitly granted scopes |
| `/operations/membership/` | Membership review and finance/rights controls, with live trial guards |
| `/operations/institutional/` | Recorded office terms and free permanent founder/honorary designations |
| `/operations/accreditation/` | Private independent casework; annual effective dates derive from final approval, course dates remain explicit |
| `/activities/`, `/activities/<id>/about/` | Visible editorial catalog/detail in isolated local testing; hosted owner-only gate remains unchanged |
| `/operations/activities/` | Activity content/media/visibility authoring plus existing admission, guardian evidence and invitation-based attendance controls |
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

Business commands remain CSRF-protected JSON POSTs at `/operations/<action>/` as well as bounded forms. Current active authority, explicit capabilities and session/grant epoch are enforced in the service boundary; the primary additionally requires its login MFA. Unrelated Django permissions do not establish authority. See the owner-approved 2026-10-19 amendment in POL-04 and ADR-030. Do not create delegates as superusers. Synthetic fixtures do not replace identity verification or recovery procedures for real operations.

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


## Activity content authoring (isolated synthetic testing)

Create/edit an activity at `/operations/activities/`: title/dates/conditions, manually supplied AR/FR/EN descriptions, programme/audience/speakers/location, category/format, up to four named HTTPS resource/video links and an optional first PNG/JPEG image. Further images/captions are added on its detail screen (six active images, 3 MiB upload each). Preview the editorial page, then explicitly Show activity. Existing records default hidden after migration0013. Hiding immediately removes the new public editorial page/images; existing authenticated participation/history stays separate.

Publish/hide/upload/remove are independent delegated choices. Editing a visible activity or adding a live image additionally requires publication permission. Primary-only hosted trial gates remain in force. See ADR031; no real data, automatic external video loading, storage service or deployment is introduced.

### Optional public activity translation

See [ADR032](docs/ADR-032-public-editorial-gemini-translation.md). Activities can generate two translations for preview/editing, translate-and-publish directly, or accept/publish the current text. Existing target translations require explicit replacement. Public text only (8000 source characters maximum); never submit private member/case data. Ordinary visits/saves do not generate translations.

After migration0014, an operator may privately configure `ANTHEEC_GEMINI_API_KEY`, `ANTHEEC_GEMINI_ENABLED=1` and `ANTHEEC_GEMINI_FREE_PROJECT_CONFIRMED=1` **only with a Google AI Studio project that has no billing linked**. These flags cannot inspect or guarantee Google's billing state. Do not link billing, paste credentials into chat or commit them. No paid fallback/retry, no additional hosting resource. Disabled/missing/quota-limited providers preserve the form without publication; manual translations remain available. Repeated successful generation keys use the bounded 30-day cache; global limit20 attempts/day, including failures. Provider integration and translation quality still require owner real-key testing; synthetic CI does not establish live functionality.
