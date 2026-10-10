# Institutional cards — owner-authorized Phase 1

Authorization: owner instruction “ANTHEEC — Phase 1 Execution Authorization”, 2026-10-10. Starting live main: d4bd125c75450c7fc530bcb686336e72e1ceab41 (PR #14). Issue #15 tracks this increment. This authorization adds institutional cards; POL-01–08 remain unchanged. Historical engineering proposals do not override this instruction.

## Approved rules and implementation

President and vice-president cards are additional documents, independent of ordinary/professional membership. InstitutionalRole references the existing Person; founder, president, vice-president and membership may coexist. No Django user, group, privilege or delegation is created by issuance.

Office records require administrator-entered legal reference and explicit start/end dates. No fixed duration is inferred. The existing technical date interval is [start, end), with the UI identifying end as exclusive; operators must record the legally established boundary accurately. Founder records have no end, no quote/payment and no renewal. A unique founder designation per person prevents repeated grants; reissue keeps that designation.

Every issuance uses existing encrypted credentials, unique serial/QR digest, printed additional code, transactional command/idempotency, outbox and audit services. Public verification remains the seven-field allowlist. QR or reference plus code is required; legal references, administrative reasons and contact details remain private. Browser labels and printable institutional cards support AR/FR/EN; machine verification codes remain stable.

Public status is derived from current institutional state and term on each request. Suspension, cancellation, termination and document replacement affect verification immediately. A replacement appointment links its predecessor and terminates that previous eligibility atomically. Document reissue voids the predecessor but cannot extend its legal term or revive suspended/ended eligibility. Records and audit events are retained through protected relations; no deletion interface exists.

Technical duplicate protection prevents overlapping active/suspended terms for the same person and same office, serializes commands under the existing Authority lock, and enforces document version uniqueness in PostgreSQL. No new global office headcount rule is invented. Terminated offices cannot reactivate; another recorded appointment is required. Permanent founders may reactivate after a reasoned cancellation through their original record.

## Minimum protected administration

`/operations/institutional/?lang=ar|fr|en` lists the latest 100 records and grants roles to an existing noticed Person. Detail pages record state decisions, show legal dates/reference, all document versions and relevant decision/reissue audits, and replace documents. The Wagtail menu links to this register. Forms use CSRF, scoped choices and per-command UUID keys. Existing live primary/delegation, TOTP/session epoch and recent password/factor checks apply; a cardholder receives no administrative access.

The baseline 0001-to-0002 migration preserves existing membership/accreditation/registration documents and encrypted credentials. It does not infer institutional eligibility from old membership categories. All examples/tests are synthetic. Printable HTML is a development artifact; no signed production PDF, deployment, external notifications, real records, new fee or later phase is authorized.

## Validation status

Local SQLite: 91 CMS/governance tests, 85 passing and six PostgreSQL concurrency cases skipped. Six metadata tests, validator, dependency/system and migration drift checks are required. PostgreSQL CI and external review of the PR head are required before merge; authoritative final evidence is recorded in the PR. This file records implementation scope, not an advance claim of acceptance.
