# ANTHEEC decision register

Owner policy authority: APPROVED_POLICIES.md, SRC-08, current continuation instruction dated 2026-10-10. No MHIOS rules imported.

| ID | Current status | Decision and evidence |
|---|---|---|
| ADR-001 | Owner-approved | Independent ANTHEEC project |
| ADR-002 | Owner-approved boundary | Synthetic design/development/testing only; production/real-person operations blocked pending verified legal/security readiness; no paid service authorized |
| ADR-003 | Superseded in part | The old blanket prohibition of automatic accreditation is superseded by POL-01: third-tier approval/renewal jointly grants professional association accreditation and separate gold card/certificate; lower tiers do not |
| ADR-004 | Tested development architecture | Django/Wagtail modular monolith; PostgreSQL CI evidence in PR #2. Production architecture/readiness not accepted |
| ADR-005 | Engineering choice | Atomic authority-locked commands, scoped idempotency and durable render outbox; synthetic PostgreSQL tests required on current head |
| ADR-006 | Owner policy resolved; technical calendar | POL-02 early/late renewal, POL-03 ongoing current prices; exclusive end and Feb29→Feb28 technical rule explicitly permitted by source §11 |
| ADR-007 | Owner policy resolved | POL-05 QR or serial+additional code, full name/type/reference/dates/status; prior notice; optional directory separate; contacts/internal reasons excluded |
| ADR-008 | Deferred | Tighri, electronic gateway, WhatsApp, external mail/translation, branch accounts require separate scope |
| ADR-009 | Owner-approved | POL-04 single primary director, full operational delegation permitted, no second electronic approval; MFA/audit/reauth/immediate revocation/recovery |
| ADR-010 | Owner-approved | POL-07 appropriate minor participation through guardian explicit consent and administrative admission; technical profile deduplication documented |
| ADR-011 | Owner-approved | POL-08 reasoned suspension/cancellation/reactivation/reissue/exemption/refund; preserve original history and invalidate replacements |
| ADR-012 | Open legal/security gate | Detailed retention/CNDP/privacy/hosting/minor/backup/rights requirements are not completed or assigned invented durations |

Owner amendment 2026-10-19 (POL-04/ADR-030) removes the previous 5-minute sensitive reauthentication constant and delegated administrative MFA; the primary verifies a second factor at login only. Other technical constants (verification entropy/rate limits, account-linked participant keys) remain engineering choices within authorized synthetic design/testing, not new organizational rules. Their adequacy needs security/readiness assessment. Historical decisions are retained in Git; conflicting proposals are not current authority.
