# ADR-021 — Declared applicant capacity and local verification correction

Date: 2026-10-16
Status: prepared; exact-head CI and review pending

## Owner decision

The owner approved administrative contact phone, profession/specialism/study field, and a required declared applicant capacity independent of the requested membership tier. Options: psychologist, psychotherapist, family counsellor, coach, therapeutic coach, psychological guide, psychological counsellor, student, beneficiary/interested person, and Other with a required explanation. These are declarations for review, not credentials, licences, authority or automatic accreditation. No clinical status or diagnosis is collected. Account creation continues to collect credentials only; profile and application forms collect their respective fields.

## Boundaries

Phone/profession are private profile fields. Capacity, Other explanation and profession are preserved with each new application; renewal carries the prior declared capacity and records current profession. Existing rows remain blank, never inferred or falsely backfilled. Profile correction does not rewrite prior applications or issued identity/artwork. Private application screens expose the declaration and notice to the owner/authorized administrator; public verification, directories and PDFs do not gain these fields. Audit details exclude phone, profession and free-text explanation. Existing idempotency and account locks apply.

Phone is validated as a contact string with 7–15 digits; this is not proof of ownership. New profile browser submissions require phone and profession/study field. New self-service applications also enforce completed profile data at both browser and command boundaries; legacy memberships can still renew without fabricated backfill. Legacy internal administrative callers remain compatible and do not erase fields they omit. Other uses conditional browser display with server-side validation and an accessible no-JavaScript fallback. AR/FR/EN form buttons describe signup, login, profile saving and application submission rather than recording an administrative decision.

## UAT defect

Local browser verification returned CSRF 403 with Origin null. The verification form's no-referrer policy conflicts with same-origin POST behavior; use same-origin to retain same-origin validation without sending referrers off-origin. CSRF and rejection of null/untrusted origins remain enabled. The owner tested this one-line correction locally: the new card verified active and the replaced card cancelled. This is local evidence, not a hosted deployment receipt.

## Open evidence

Owner local synthetic UAT passed general membership, image approval/reissue, AR/FR/EN previews, French PDF download equality, old/new verification, suspension/reactivation, early renewal (2027-10-16 to 2028-10-16) and anonymous download login gate. Affiliate application #3 quoted 500 MAD; approval/output not yet accepted. Large local response delays remain unresolved, explicitly deferred by owner. New intake UI owner acceptance, full CI/review and private deployment remain pending. Hosted public registration/payment/issuance gates, resources/plans, Tighri and MHIOS remain untouched.
