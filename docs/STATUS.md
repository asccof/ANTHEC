# Execution ledger

## 2026-10-10 — independent baseline and multilingual CMS increment

Repository: `asccof/ANTHEEC`; main bootstrap: `4df3f6d`. Issue #1; feature branch `eng/001-003-multilingual-foundation`. Repository is public: source attachments and personal/contact data are excluded. No MHIOS files or governance imported.

Completed: seven-artifact source analysis, deduplicated executive DOCX, source hashes, requirements traceability, conflict/decision register; Django/Wagtail text CMS with AR/FR/EN locales, manual translation, draft/publication and revision history; synthetic seed; production configuration disabled; memory-only email, disabled external translation, no public media route.

Local evidence: 6 baseline tests and 28 CMS/translation tests passed on SQLite; `manage.py check` clean; migrations applied and synthetic AR/FR/EN seed succeeded. The seed slug collision with Wagtail's default home was fixed before delivery. Dependencies are locked to Django 5.2.18 and Wagtail 7.4.3 LTS; final checks use an isolated environment. PostgreSQL CI is proposed and must be verified on the PR head, not inferred from SQLite results.

Not complete: MFA, reviewer separation, automatic translation/review workflow, scheduled-publication acceptance, role/record-level business authorization, membership/payment/accreditation/event/partner workflows, private uploads, generated cards/QR/PDF, security/load/restore acceptance. AC-01–14 and T01–12 remain planned until their full criteria are demonstrated. ENG-003 is a partial technical proof; editor usability and broader workflow checks remain required.

Pending owner decisions: membership benefit wording and third-tier name; validity/renewal/campaign rules; approval authority; public verification fields; collection/retention/deletion and guest/minor eligibility. These do not block the text CMS.

No production deployment, paid subscriptions, external provider calls, real-person records or clinical data. Review and CI results are linked in the PR; no external Codex review is claimed until returned against the final head.

PR #2: https://github.com/asccof/ANTHEEC/pull/2. PostgreSQL CI passed on initial head 6da8584. Codex identified missing standalone validator CI invocation and unsafe replacement of an existing leaf homepage; both addressed with targeted seed regressions. Updated-head CI and review remain required. Proposed domain contracts are in draft PR #4 (issue #3); they are not approved business policy.

## 2026-10-10 — expanded contracts and executable backlog / issue #3


Drafted DOMAIN_CONTRACTS.md: typed relations and database constraints; state/actor/prerequisite/effect tables; independent membership/accreditation; proposed least-privilege permissions; justified data fields and unresolved retention; idempotency conflict handling, durable outbox and uncertain-delivery limits; proposed routes/error envelopes and concrete acceptance scenarios. POL-01–08 remain owner decisions. No business application code or approved policy was introduced in this documentation increment.

Opened execution issues #5–10 for CMS/MFA, membership/payment/issuing, accreditation, activities, partnerships/branches and non-production readiness. BACKLOG.md records dependencies and gates. PostgreSQL CI succeeded on foundation head `6da8584e3495a8376855bafea3f7ae583c20112a`; Codex reported two findings (missing direct baseline-validator CI invocation and protection of preexisting leaf homepage during demo seeding). Foundation fixes/re-review are tracked in PR #2; that historical success does not validate a later head.

Branch-protection read returned integration-access 403. Protection is therefore unverified; no security setting is represented as enabled.

## 2026-10-10 — foundation accepted in Git

PR #2 merged into main as `46e1ba242170ab638ff828d6f7bceab2e1a2cc46`. Reviewed head: `b6ce04ea396e85f9fd92ea49cc37a900ce5eede9`. PostgreSQL CI runs 38055593398 and 38055588826 succeeded; direct validator, 6 baseline tests and 28 CMS/translation tests passed. Codex completed the updated-head review without major issues; both prior findings are resolved. This accepts only the bounded CMS foundation, not full platform or business-policy acceptance.

PR #4 is retargeted to main for the expanded proposed contracts and backlog. Draft 0.2 supersedes the earlier contract draft; none of POL-01–08 is marked approved. An initially reused local virtual environment showed third-party migration drift; a new environment installed from the committed requirements passed dependency consistency, system/migration checks and 28 CMS tests. No source/package migration workaround was committed.

## 2026-10-10 — contract review corrections

Codex review of 8702554f0df973610822120a1aa7b90bd66f121e identified two documentation inconsistencies: stale foundation state in BACKLOG.md, and an unsubstantiated policy-to-source trace claim. The next revision marks the bounded foundation accepted while retaining full CMS acceptance as pending, and adds an explicit POL-01–08 to F/source mapping distinguishing source requirements, gaps and new proposals. Re-review/CI of the corrected head is required; this entry records fixes, not a review pass.

## 2026-10-10 — owner-approved policies / issue #13, implementation under review

Verified starting main `97f16322a41318c9e5163ef8c18c986c1a68caa5`: PR #2 foundation and PR #4 proposed contracts are already merged. Their delivery is not repeated. Owner-supplied ANTHEEC.docx v1.0 (SRC-08) and current implementation instruction approve POL-01–08. APPROVED_POLICIES.md/current contracts/ADRs supersede conflicting proposals. Issue #12 is closed as an approved decision queue; #5–8 have been corrected, while full feature/readiness work #5–10 remains open.

Implemented on `eng/013-approved-policy-core`: transactional effective prices/fixed quotes/cash-transfer proof/exemptions/refunds; approval/early-late renewal and free indefinite grants; automatic linked third-tier annual professional accreditation with separate gold card/certificate; independent accreditation duration checks; encrypted printable HTML, typed document/serial/version/outbox, replacement/history; QR/reference-plus-code allowlisted verification without name search; primary-only delegation management, TOTP/password MFA and one-use hashed recovery, session epoch revocation and sensitive-command reauthentication/audit; guardian consent evidence, administrative event admission/capacity, cancellation and unique attendance. No full independent assessment/private upload workflow or finished membership/admin/event forms is claimed.

Local SQLite: 58 application/CMS tests pass; three PostgreSQL-specific concurrency tests are skipped locally and must pass in CI. Six metadata tests and standalone validator pass. Django checks and migration drift are clean; pinned dependencies pass `pip check`. Verification error redirection through LocaleMiddleware was found by tests and fixed; recursive future-renewal state propagation is covered. Final CI and external Codex review are not yet accepted in this entry; their exact heads/results will be linked in the implementation PR.

Remaining: full CMS translation/media/scheduling acceptance; managed-profile and application/event forms, cross-account participant identity handling, independent accreditation case/private evidence/fees, optional directory, complete financial operations and production document design; partnerships/branches; bounded rate-bucket cleanup, protected backups/restore and key rotation/recovery, accessibility/load/security and independent legal readiness (retention/rights/CNDP/notices/hosting/minors). No new organizational policy is introduced or awaiting reconfirmation. Operational settings remain private; detailed legal obligations must be reviewed, not invented. Synthetic data only, no deployment or external delivery.

Initial PR #14 PostgreSQL run 38060188719 failed on head `c2758f916b49c50ca51038a82d9361b7768214ca`: SELECT FOR UPDATE included a nullable joined renewal/invitation relation. Corrected queries lock the document/application itself; the prior term is locked explicitly and the command boundary already serializes sensitive decisions. Additional regression tests reject malformed JSON field types, repeated exemptions and missing/malformed guardian-consent text/fields. Updated local result: 60 passing application/CMS tests plus three PostgreSQL-only tests skipped; updated-head CI/review still required. PR: https://github.com/asccof/ANTHEEC/pull/14.

PostgreSQL CI run 38060378970 passed all 63 application/CMS tests and six metadata tests on `5d08789968bf8cace704441539881048e2281a75`, including duplicate approval, last-seat/attendance and refund-cap concurrency. Codex review of the initial head returned two P2 findings: absent consent-text/version validation (already corrected in that updated head), and future invitations allowing premature attendance. The next correction makes future invitations pending, checks consent snapshots at administrative admission too, and adds activity-date-boundary and missing-snapshot regressions. Targeted local governance tests: 34 pass, three PostgreSQL-only skipped. Updated full CI/re-review remains required before acceptance; no current-head review pass is inferred from earlier evidence.

## 2026-10-10 — authorized institutional Phase 1, issue #15

Re-fetched live main d4bd125c75450c7fc530bcb686336e72e1ceab41 (merged PR #14); no open PR remained. Previous policy-core work is not repeated. Branch eng/phase1-institutional-cards implements the separately owner-approved institutional package described in INSTITUTIONAL_CARDS_PHASE1.md: recorded role eligibility, independent cards, term/state verification, protected AR/FR/EN grant/decision/reissue interfaces, additive migration and regression/concurrency coverage. Local 91-test suite succeeds (85 passing, six PostgreSQL-only skipped). PostgreSQL CI and updated-head Codex review remain required before acceptance; final evidence belongs to the focused PR. No Phase 2, production, real records or new organizational policy is introduced.

First Phase 1 PostgreSQL CI run 38063099746 passed all 90 application/CMS tests and six metadata tests on 74cc73d925b754cd16b4bb8dd751cef8f9f5edc1. Self-review then identified a localization collision: a holder name matching a machine vocabulary key could be translated. Translation is now restricted to type/document_type/status, with a synthetic-name regression. Updated-head CI and review are required.

## 2026-10-10 — Phase 2 package A prepared / issue #17

Live main verified at 6196e32704321b21e8deb4717c44673fd3b5242e; Phase 1 PR #16 merged and no open PR found. Owner approved the Phase 2 mandate. MEMBERSHIP_INTERFACES_PHASE2.md records the three bounded packages and service/interface gap map. Package A adds synthetic member account/profile/application interfaces with ownership, notice, CSRF, audit, replay and concurrency safeguards. PostgreSQL CI and external review of its final head are required before acceptance. No Phase 1 rebuild or POL-01–08 amendment.

## 2026-10-10 — Phase 2 review gate blocked; package B prepared

Package A PR #18 head 7012a6489470b04182c7cb4d006c1a2460d284c6 passed PostgreSQL CI run 38064423647 (101 application/CMS tests without skips plus six metadata tests). Initial local pass wording was corrected in the PR: the synthetic password-change fixture resembled its username and was rejected; fixture corrected without weakening password validators, full tests rerun. Codex rejected review requests due to exhausted account review usage. PR remains draft/unmerged; no paid service enabled. Live main is unchanged at Phase 1.

Package B is prepared on a dependent branch: protected review/rejection, payment/exemption/refund/state/reissue and deliberate legacy account linking with scoped choices and existing MFA/audit/transactions. Stacked drafts allow useful authorized preparation while preserving the merge gate; dependency acceptance, retargeting, live-main CI and exact-head review are mandatory before merge. This is not an acceptance or production claim.

## 2026-10-10 — Phase 2 recovery: package A accepted, B reconciled

PR #18 exact head e56ba467b0d55af8247a7c79cf10a696ff0cf793 passed PostgreSQL 16 CI 38065371450 (102 application/CMS tests without skips, six metadata tests and required checks). Codex completed exact-head review without major issues; no inline findings. Merged as 2f67eb47e4dc2aa8a8364d6fb8e03c1f40040bef. This supersedes the historical quota blocker above.

Package B PR #19 is reconciled onto that live main using only B-owned changes; shared password/MFA corrections remain inherited from A, without duplicate commits. Updated-head PostgreSQL CI and exact-head Codex review remain required before B acceptance. Package C remains a preserved draft and gated. Synthetic only; no policy changes or deployment.

Package B reconciled head 0d0904aed0abd4cdd1b05307f610fb556e4f2d66 passed PostgreSQL CI 38066515876 (111 application/CMS tests, six metadata tests, no skips). Codex returned one P2 documentation finding: the interface specification still described the superseded package A quota blocker as current. Corrected it to distinguish historical evidence from A acceptance and B reconciliation. Updated-head CI/re-review remain required.

Second package B review returned one P2 interface finding: the reauthentication navigation label was missing in all three locales. Added the explicit AR/FR/EN label and a regression asserting visible challenge links on every administrative page; existing MFA behavior remains unchanged. New-head PostgreSQL CI and review remain required.

Third package B review found a P2 state-selector issue: an unbound form defaulted to active after suspension/cancellation. It now initializes from the actual membership state; a regression verifies selected suspended/cancelled states and unchanged linked accreditation after GET. New-head CI/review required.

## 2026-10-10 — package B accepted; package C reconciled

PR #19 final head e9ff6d31907fa752fc33c743afa1811a671eccdc passed PostgreSQL 16 CI 38067472904 (112 application/CMS tests without skips plus six metadata tests and required checks). Codex exact-head review completed without major issues after three P2 corrections: obsolete dependency status, invisible reauthentication label, state selector defaulting active. All threads resolved. Merged as 16a5772e94809f57708d792198e9e5361234435e.

PR #20 is reconciled onto this accepted main using C-owned changes only. Retains all A/B fixes and history; supports owned renewal/records/documents, institutional integration, localized printing/verification/MFA presentation and public membership navigation. Complete synthetic CSRF-enforced journey and concurrent renewal regressions included. Historical stacked C PostgreSQL run 38065570972 passed its 120-test tree, but updated-head PostgreSQL CI and exact-head Codex review are required for acceptance of this reconciled candidate. Current suite has 121 tests with the inherited B regression. No new migration, policy decision, external delivery or deployment.
