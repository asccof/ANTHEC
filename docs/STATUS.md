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
