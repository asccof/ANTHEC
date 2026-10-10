# Execution ledger

## 2026-10-10 — independent baseline and multilingual CMS increment

Repository: `asccof/ANTHEEC`; main bootstrap: `4df3f6d`. Issue #1; feature branch `eng/001-003-multilingual-foundation`. Repository is public: source attachments and personal/contact data are excluded. No MHIOS files or governance imported.

Completed: seven-artifact source analysis, deduplicated executive DOCX, source hashes, requirements traceability, conflict/decision register; Django/Wagtail text CMS with AR/FR/EN locales, manual translation, draft/publication and revision history; synthetic seed; production configuration disabled; memory-only email, disabled external translation, no public media route.

Local evidence: 6 baseline tests and 26 CMS/translation tests passed on SQLite; `manage.py check` clean; migrations applied and synthetic AR/FR/EN seed succeeded. The seed slug collision with Wagtail's default home was fixed before delivery. Dependencies are locked to Django 5.2.18 and Wagtail 7.4.3 LTS; final checks use an isolated environment. PostgreSQL CI is proposed and must be verified on the PR head, not inferred from SQLite results.

Not complete: MFA, reviewer separation, automatic translation/review workflow, scheduled-publication acceptance, role/record-level business authorization, membership/payment/accreditation/event/partner workflows, private uploads, generated cards/QR/PDF, security/load/restore acceptance. AC-01–14 and T01–12 remain planned until their full criteria are demonstrated. ENG-003 is a partial technical proof; editor usability and broader workflow checks remain required.

Pending owner decisions: membership benefit wording and third-tier name; validity/renewal/campaign rules; approval authority; public verification fields; collection/retention/deletion and guest/minor eligibility. These do not block the text CMS.

No production deployment, paid subscriptions, external provider calls, real-person records or clinical data. Review and CI results are linked in the PR; no external Codex review is claimed until returned against the final head.
