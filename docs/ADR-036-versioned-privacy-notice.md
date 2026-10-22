# ADR 036 — staged versioned privacy notice and acknowledgement evidence

Date: 2026-10-22. Authority: owner direction to complete ANTHEC launch-readiness work; POL-06 and the supplied internal privacy policy v2. Status: prepared for independent code review; not legal acceptance or hosted activation.

## Decision

Provide a bounded AR/FR/EN privacy notice and a distinct unchecked reading acknowledgement for account creation, profile editing, membership application/renewal, portrait upload, activity participation and partnership requests. Preserve the separate portrait/verification/guardian/partnership declarations. No marketing consent, optional directory, clinical records or external delivery is introduced.

Evidence is an existing private Audit entry: actor when authenticated, explicit purpose and resource subject, server timestamp, complete localized notice and acknowledgement, version, configured publication date and SHA-256. No IP/device fingerprint is added to this evidence. Capture runs in the same transaction as the submitted resource and rolls back on failure; member-command replay does not duplicate evidence. The service boundary rejects missing/obsolete versions before replay lookup when enabled. Nested intake portrait creation carries the already validated acknowledgement and records its own purpose without altering existing issued snapshots.

`ANTHEEC_PRIVACY_NOTICE_ENABLED` defaults off. Hosted activation accepts only explicit `0`/`1`, permits `1` only in operational mode and requires `ANTHEEC_PRIVACY_NOTICE_PUBLISHED_ON` in canonical ISO format. Source deployment alone does not publish the notice, require new acknowledgements on live forms or claim that formalities are complete. Do not activate the hosted flag as part of this increment. `/privacy/` returns 404 when disabled. Local synthetic tests can enable the staged feature separately.

Version `ANTHEC-privacy-v2-20261022` identifies this copy, distinct from its actual publication date. Update the version whenever the notice or acknowledgement text changes. Historical full-text evidence remains preserved. Reading acknowledgement is not represented as an all-purpose legal processing consent, administrative acceptance, CNDP approval or a governmental professional licence.

## Boundaries still open

Provider/processing/transfer formalities, independent legal acceptance, full retention/rights execution and independent security acceptance remain unverified. The notice explains the existing president contact channel and limitations; this increment does not implement automated erasure, a rights-request case management system, retention jobs or statutory deadlines. Do not mark `check_release_readiness`'s privacy/legal gates verified because a flag or checkbox exists.

Original private policy attachments are not copied into this repository. Public copy summarizes approved purposes and boundaries, including restricted verification, portraits, minors, hosting, cookies and contact; translations and actual publication need final content/legal acceptance before activation.

## Validation

Focused tests exercise unchecked localized fields, direct service/API rejection, exact snapshot/digest, signup without privilege escalation, anonymous partnership evidence, atomic member replay, application intake propagation, closed staging and hosted configuration guards. Browser acceptance runs the staged notice and signup fields in all three languages and checks mobile/desktop overflow while preserving existing public QR verification and activity checks. Exact-head full PostgreSQL CI and external review are recorded in the PR; preparation is not reported as an executed hosted acceptance.
