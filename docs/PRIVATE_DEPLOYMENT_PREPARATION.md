# ANTHEC private deployment preparation — 2026-10-12

This increment prepares owner-only synthetic testing. It is not a public launch,
security certification, paid-resource authorization or merge/deployment approval.
No Render resources, Tighri services or DNS records have been changed.

## Verified baseline and boundaries

- Live `asccof/ANTHEC/main`: `6f9c22e227334d2bf480038cd3bc3e7ccc7afa09`.
- PR #23 merged on 2026-10-12. Its final head `16a5ede867e172b841a837ee8030fd4b89c5e7b4`
  passed PostgreSQL 16 CI [38251654134](https://github.com/asccof/ANTHEC/actions/runs/38251654134).
- The connector lists PR-triggered Actions only. It returned no main merge-SHA
  runs; this is not evidence of a failed or absent push workflow. Combined status
  also returned no legacy statuses. New-PR CI must be checked independently.
- Previous exact-final-head external review hit a Codex usage limit; the last
  completed external review covered `d79e6687a2`, not the merged final head.
- Existing worktrees and drafts are preserved. This branch starts from live main.
- Card/certificate rendering code, artwork/fonts/logo, localized titles,
  POL-01–08, fees, term rules and participation proof templates are unchanged.

## Exact proposed architecture

Reuse the existing owner's Render login, in a **new ANTHEC-only Hobby workspace**
(or an existing verified ANTHEC-only workspace). Do not move or edit Tighri.
Separate service names alone do not provide private-network isolation: Render
services in one workspace/region share a private network. A distinct workspace
avoids buying Pro solely for environment isolation. Render permits up to five
Hobby workspaces; actual account capacity and billing are not yet inspected.

| Component | Prepared configuration |
| --- | --- |
| Web | `anthec-owner-test-web`, Docker, Frankfurt, `0.5c-512mb`, one Gunicorn worker/two threads; non-root UID 10001 |
| Database | `anthec-owner-test-db`, PG16, `0.1c-256mb`, exact database/user `anthec_owner_testing`; external IP allowlist empty, internal URL, TLS required |
| Runtime | `antheec_app.settings.production`, explicit `ANTHEEC_MODE=owner-testing`; public production still rejected |
| Access | Primary authority only; active account, password, TOTP MFA and authority epoch; no delegate access to this test deployment |
| Public surface | Login/logout, sanitized health probe and public static code/brand assets; all dynamic content is private; no search indexing/cache |
| HTTPS | Render TLS ingress, exact allowed hostname/CSRF origin, secure cookies, redirects, no-referrer, staged one-hour HSTS |
| Protected assets | Existing normalized, encrypted PostgreSQL portrait/signature/stamp payloads, primary-only upload/approval, recent reauthentication and immutable audit/snapshots |
| Other media | Default filesystem upload/read/public URL disabled; no ephemeral upload loss and no new disk subscription |
| Issuance | Shared service gate rejects every document issuance and official PDF/outbox generation; no scheduled document worker |
| Public workflows | Registration, member applications/renewal, verification and document routes closed; payment/refund commands blocked |
| Email | Dummy backend: no SMTP subscription, external notifications or email password recovery |
| Jobs | No Redis/Celery/worker/cron service for this phase; run no outbox processor; existing jobs fail closed |
| Deployment | Blueprint kept at `deploy/render.owner-testing.yaml`; previews and auto-deploys off; no webhook/automatic main deployment |

The web address is internet-reachable for login, but application data is
authenticated and owner-only. This is application-level restriction, not a VPN
or Render network IP allowlist. No real-person records, authentic private assets
or previous production database may be imported for initial synthetic testing.

Only exact HTTPS origin is accepted. Start with the isolated service's
`onrender.com` hostname; add `anthec.com` only after ownership and DNS control are
verified. The container port must remain behind Render ingress, which is the
only trusted source of `X-Forwarded-Proto`. Gunicorn access logging is disabled;
Django request/security exception output is suppressed to avoid request/secret
disclosure. Existing database-backed audit records remain available to the owner.
Confirm ingress headers, operational logs and memory use on the actual service.

## Secrets and primary setup — through secure account surfaces only

| Value | Owner action |
| --- | --- |
| `ANTHEEC_SECRET_KEY` | Generate a unique random >=50-character secret privately; set only in ANTHEC Render environment. Render's default `generateValue` is 44-character base64, so this Blueprint requests a private value instead. |
| `ANTHEEC_DATA_KEY` | Generate a new Fernet key privately; never reuse Tighri/test keys. Keep a separately protected recovery copy. Do not casually rotate it: existing encrypted payloads would become unreadable. |
| `DATABASE_URL` | Blueprint references only the dedicated database; never paste credentials into chat, logs or the public repository. |
| `ANTHEEC_PUBLIC_ORIGIN` | Exact HTTPS ANTHEC service origin, no wildcard/path/port. |
| `ANTHEC_BACKUP_KEY` | Separate offline Fernet key in the owner's secret manager. Not required in the web service; needed by the offline backup utility. |

After merge approval and paid-service approval, use the ANTHEC-only Render shell
to run migrations via the prepared pre-deploy command. Do not seed real members.
Create a pseudonymous primary superuser interactively with an `example.invalid`
email; then run `python manage.py bootstrap_authority <synthetic-username>`.
Log in over verified HTTPS, enroll TOTP at `/security/enroll/`, retain recovery
codes in the owner's secret manager and verify `/admin/` access. Never send the
password, TOTP secret, recovery codes, signature or stamp via chat. The bootstrap
command forbids replacing an existing primary and preserves synthetic-only rules.

## Storage and recovery

Paid Render PostgreSQL supplies continuous PITR: Hobby retains three days;
Pro retains seven. Logical exports are retained by Render for seven days.
Free PostgreSQL has no managed backup/recovery, so it is not the prepared plan.

`tools/encrypt_backup.py encrypt SOURCE TARGET` wraps a private logical export
with authenticated Fernet encryption, using `ANTHEC_BACKUP_KEY`. It creates an
exclusive 0600 output, never prints secrets and rejects shared data/backup keys.
`decrypt` similarly creates a new protected output; preserve plaintext only on
an encrypted owner workstation and remove it after the approved restore drill.
The small-export tool is bounded to 128 MiB of plaintext; do not use it as a
large-database streaming backup solution.

Recovery requires **both** the database export/PITR and the original
`ANTHEEC_DATA_KEY`; possession of a database alone cannot recover encrypted
credentials/private images. Retain backup key, data key and database credentials
separately from exported files. Restore into a new ANTHEC-only database, validate
decryption, authority, protected access and document integrity, then change only
ANTHEC's connection. Never restore into or change Tighri. PITR restoration creates
an additional paid instance, so a live drill requires explicit budget approval.

CI's `tools/validate_recovery.py` is restricted to the synthetic CI database. It
exports PostgreSQL, encrypts/decrypts the export, restores to a separate database
without drop/clean, and verifies decryption of a synthetic encrypted audit value.
This is engineering recovery evidence, **not** a completed Render disaster drill.
Initial backup exports are manual; no off-provider backup schedule, destination
or retention policy is activated. Before authentic private assets/real records,
approve and verify off-provider encrypted backups, key escrow and live recovery.

## Verified public prices and domain result

Public price references checked 2026-10-12; account-specific credits, taxes,
payment method, quotas and existing charges are unknown until connection.

| Incremental item | Monthly estimate, USD |
| --- | ---: |
| ANTHEC-only Hobby workspace | 0 |
| Web `0.5c-512mb` | 7 |
| PostgreSQL `0.1c-256mb` | 6 |
| Initial total, within included usage/storage | **13** |
| Optional 2 GiB web instead, if actual memory testing requires it | **31 total** |

No worker, Redis, SMTP or persistent disk is needed in this restricted phase.
Paid PG includes 1 GB storage; additional storage is $0.30/GB/month. Hobby includes
5 GB outbound bandwidth and 500 build minutes; listed overages are $0.15/GB and
$5 per additional 1000 build minutes. Two custom domains are included, additional
ones $0.25/domain/month. These are estimates, not an authorized subscription or
an account-specific final invoice. 512 MiB is provisional until Render memory and
protected-upload tests are observed; no public/PDF throughput claim is made.

The authoritative Verisign RDAP lookup returned HTTP 200 for **ANTHEC.COM**, with
registration date 2008-11-06 and `client transfer prohibited` status. The domain is
already registered, not available as a normal new registration. This does not
identify its owner or prove that the project owner lacks control. No purchase,
transfer, registrar account inspection or DNS change was performed. Its actual
acquisition/renewal price cannot be quoted without ownership/registrar evidence.
Namecheap's ordinary .com reference price was $10.98 first year / $18.48 renewal,
plus $0.20 ICANN, with a conditional new-customer promotion; these rates are **not
a purchasable ANTHEC.COM offer**.

Sources:
- https://render.com/pricing
- https://render.com/docs/compute-plans
- https://render.com/docs/team-members
- https://render.com/docs/private-network
- https://render.com/docs/blueprint-spec
- https://render.com/docs/postgresql-backups
- https://render.com/docs/custom-domains
- https://render.com/docs/build-pipeline
- https://render.com/docs/outbound-bandwidth
- https://rdap.verisign.com/com/v1/domain/anthec.com
- https://www.namecheap.com/domains/registration/gtld/com/
- https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

## Validation and release gates

Relevant tests cover private access, actual OTP sessions, primary/delegate
separation, login throttling, service-level issuance/payment/application guards,
disabled ephemeral media, strict runtime settings and offline backup integrity.
Full existing multilingual/PDF/protected-asset/concurrency tests remain required
on PostgreSQL. CI also builds the non-root Docker image and collected static
manifest. Production checks intentionally retain `security.W005`/`security.W021`
because HSTS is staged without subdomain/preload commitments; no other deployment
warnings are accepted by the regression. No migration or design change is added.

Validation results and exact external review are recorded on the preparation PR
and the execution ledger as they complete. Do not infer passing results merely
from this prepared checklist.

| Remaining gate | Owner/execution action |
| --- | --- |
| Render account unavailable | Install/connect Render using the existing owner's account; permit read-only account/workspace/service/billing inspection first. |
| Tighri isolation not account-verified | Confirm ANTHEC-only workspace capacity; verify target IDs/names and absence of shared environment groups; change nothing in Tighri. |
| Review/merge | Successful required CI, exact-head external review, then explicit owner approval before merging this PR. |
| Paid resource creation | Approve exact incremental cost after account inspection; no resources have been created. |
| Private first deployment | Apply only the approved ANTHEC Blueprint, verify HTTPS/proxy/DB TLS/static/owner-MFA/negative access/logs/memory checks with synthetic data. |
| Domain | Confirm whether the owner controls ANTHEC.COM through the registrar; otherwise agree on another available domain or separately approve acquisition. |
| Real/private assets and recovery | Approve backup destination/retention/key escrow; perform isolated Render recovery before importing authentic assets or real records. |
| Public workflows / issuance | Remain disabled; require a new explicit authorization and reviewed implementation. Participation remains NOT ISSUED. |

Stop at the owner review gate. No merge, purchase, deploy, external application,
real-data import or Tighri modification is included in this preparation PR.
