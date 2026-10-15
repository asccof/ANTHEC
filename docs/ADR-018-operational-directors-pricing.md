# ADR-018 — director and prospective pricing interfaces

Status: prepared for exact-head CI/review, 2026-10-15. Authority: POL-03/04 and current owner instruction following acceptance of PR33.

Provide administrative AR/FR/EN director and membership-price screens over existing authorized commands. Only the primary may read/manage the director register; the primary is excluded from targets and cannot be replaced. Other superusers are excluded. Active/inactive delegation changes require an explicit decision, confirmation, documented reason and recent MFA; existing epoch changes immediately revoke previous sessions and command replays. The menu hides director management from delegates; server-side checks remain authoritative. No account password, recovery token, primary transfer or automatic invitation is introduced.

Pricing is available to operational authority, as already approved. Only new future versions are inserted, with explicit UTC effective time, amount, confirmation and reason. Free founder/honorary are excluded. Existing quotes and financial records remain immutable. The existing price command accepts an optional documented reason without breaking existing callers. No actual prices are changed by deployment or fixtures.

The owner-testing gate still admits only the verified primary. A manually guarded fixture creates one synthetic nonstaff candidate with unusable password, no delegation and no credentials. Granting it does not admit it to the private site. Registration, payment/refund and official issuance guards remain intact.

Local execution environment is unavailable. No local verification is claimed: the existing GitHub CI must execute metadata validation/tests, system checks, migration drift, full content/governance tests on PostgreSQL, synthetic recovery and container validation before merge; exact-head Codex review remains required. No schema migration is added. Trial publication and owner acceptance are recorded separately. No Tighri or resource/plan changes.
