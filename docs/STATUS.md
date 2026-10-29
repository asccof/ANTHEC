## 2026-10-29 — confirmed member account controls prepared

Owner distinguishes login account cancellation/suspension/editing from membership and document status, and requests independent confirm-only state operations without the member’s password or mandatory unrelated identity fields. ADR040 adds scoped ordinary-member account controls, separate optional account/profile editing, per-account session epochs, protected administrator targets, explicit new delegation options (no existing grants changed), and distinct states in membership administration. Migration0018 is additive. Initial 109 focused/content tests passed; final hook/browser/full CI/review and hosted acceptance remain pending. No real account was changed.

## 2026-10-24 — tools entry points clarified

Owner screenshots identify the existing resources-news editorial page being opened instead of the new tools catalog. Live inspection additionally found CMS tools anchors with empty text: the new label existed only in the service-page vocabulary. Add the missing CMS vocabulary label and a regression checking visible anchor text in all three languages. Add the Tools & Resources link beside that page in its navigation dropdown and an explicit catalog button above the editorial page body in AR/FR/EN. Preserve research/news copy and existing top-level tools link. No data, schema or workflow change. Checks/review/deployment remain separate evidence.

## 2026-10-24 — tools and resources prepared

Owner requests a multilingual tools catalog with optional image/text/link, details, and a full-name/phone/email request received privately by administration for manual follow-up. ADR039 implements a public catalog and primary-only admin tools/request inbox, publication controls, signed idempotent intake, versioned acknowledgement evidence and existing workflow/rate/CSRF guards. PostgreSQL binary media stays separate from private portraits; no filesystem/provider/email activation, invented production catalog or membership/fee change. Migration0017 is additive. Exact-head CI/review and hosted rollout remain pending.

## 2026-10-23 — membership fee reminder prepared

Owner requested a nonblocking fee reminder at tier selection and a persistent pending-review/payment-contact message after submission. The intake reads current effective Price rows using the submission quote ordering, retains free founder/honorary treatment, and uses the stored quote on the private receipt. AR/FR/EN, no-JavaScript fallback and browser back restoration are included. No payment field, validation gate, price change, migration or translation-provider activation. Exact-head CI/review and hosted deployment remain pending.

## 2026-10-23 — one-submit membership intake prepared

After the official-domain cutover (PR63, live ead1377 / dep-dbdnisss728c73cj26dg), the owner requested and explicitly approved replacing separate account/profile/application steps with one form and submit. ADR038 records composed validation, an atomic account/profile/pending-portrait/application save, existing-account prefill, distinct consent/evidence purposes, duplicate guards and a private pending-review receipt in AR/FR/EN. Local focused acceptance passed 46 tests; metadata validation, 12 auxiliary tests, system/migration checks passed. Browser acceptance adds synthetic complete submissions in each language and responsive form checks. Full exact-head PostgreSQL/container/layout CI, code review and deployment remain pending. No real signup, private member update, fees/artwork/schema change or Tighri action.

## 2026-10-23 — custom domain cutover prepared

Owner purchased anthecmaroc.com and configured Porkbun ALIAS/CNAME to the existing ANTHEC service. Render confirmed apex/www ownership and issued both TLS certificates. Application canonical origin is still the existing Render hostname; DNS/TLS alone is not completed application cutover. Owner authorized continuation. ADR037 adds exact-host legacy QR redirects, an explicit default-CMS-origin sync and controlled anonymous editorial discovery. No membership, issued assets, keys, paid resources or Tighri changes. Initial local acceptance passed 100 focused/content tests and 12 metadata/backup tests; metadata validation, Django checks and migration drift checks passed. Final focused run passed 16 tests including authenticated-discovery and operational-invalid-origin regressions (overlaps the initial run). Exact-head PostgreSQL CI/review, merged code, configuration activation and live acceptance remain separate pending steps. Owner backup/key confirmations and scoped independent review materials are retained privately; legal/provider formalities remain association-managed, without an exemption/compliance claim.

## 2026-10-22 — phase-one activation and dependency audit

Owner authorized phase-one execution. Privacy notice v2 was activated on the existing ANTHEC service with actual publication date 2026-10-22; deploy dep-dbd77ejl550s73atuvdg is live on d2672b1. AR/FR/EN notice and signup GET checks passed; no existing secret/workflow flag was replaced. Rights/retention handling is documented privately for the president, with no new deletion job or claim of completed real-data erasure. Owner-local backup/key custody, provider/CNDP formalities and independent security acceptance remain unverified.

A fresh pip-audit found advisories against five direct pins (106 advisory records, including aliases/duplicates; not 106 confirmed exploitable application flaws). Stage minimal security refresh: certifi 2026.10.19, Pillow 13.0.0, pip 26.2, cryptography 50.0.2 and pypdf 6.21.1. No key rotation, schema/asset rewrite, new service or clinical data. Initial patched-pin audit reports no known vulnerabilities; final CI/review and deployed verification remain required. Existing cryptographic recovery, immutable PDF, QR/layout and bounded memory tests are acceptance gates for this update. This does not constitute a formal independent penetration-test acceptance.

# Execution ledger

## 2026-10-22 — protection enforced, recovery/performance published, privacy staged

Owner confirmed saving the concrete main protection settings. GitHub created the rule after secure owner identity confirmation; branch read now reports protected=true with `container`, `public-layout` and `validate` checks enforced for everyone. The saved form additionally required pull requests, current branches and resolved conversations, disallowed force pushes/deletion and applied protections to administrators. No bypass or additional person access was added.

PR60 final head `bc7eb7b` passed CI39790345149 (381 PostgreSQL and 12 auxiliary tests, enhanced recovery, browser acceptance twice, non-root container and constrained capacity). Final-head Codex completed with no findings at 19:40 UTC after the earlier quota block. Merged via the protected PR path as `f295308`; merge tree `49d60563f6d3e303b4123b2ca667e6d5d6577044` matches the tested tree. Existing ANTHEC deploy `dep-dbd6llafngtc73fq4qmg` went live at 19:59:34 UTC; health, verification, activities and Arabic homepage returned 200. No new service, billing, workflow toggle, private-data mutation or Tighri change.

Next bounded branch `eng/versioned-privacy` prepares ADR036: an AR/FR/EN notice and explicit unchecked, versioned, snapshotted acknowledgements in self-service and partnership requests, with backend validation and existing private audit evidence. Defaults closed and no hosted flag activation. Local focused tests passed; exact-head full CI/review pending. Rights/retention execution and provider/legal/security acceptance remain open; no CNDP reference or compliance assertion is invented.

## 2026-10-22 — full launch acceptance in progress

Constrained CI `39788446160` on `3fa698d` terminated with exit 137 during the synthetic maximum-input workload. This is a reproduced constrained-test failure, not proof of the historical hosted OOM cause. The fix downscales/crops accepted images before full-size EXIF/alpha intermediates in portrait, activity and signing-asset normalization. New orientation/alpha regressions and existing portrait/PDF/application-photo tests passed locally (38 tests plus three focused regressions). Final constrained CI remains pending. Previously issued assets are untouched.

Codex review on PR60 failed because its code-review usage quota was exhausted, not because a completed reviewer accepted/rejected the change. No purchase, review bypass or completed independent acceptance is claimed. Browser fallback for GitHub branch protection reached the login page; secure auth selection returned Google, but automated review then denied observation of accounts.google.com for missing explicit origin authority. Do not work around that rejection. Branch protection remains unchanged and blocked on safe authentication.

Owner authorized completion of launch-readiness work after PR59/main `47ac788` was published. Public institutional copy/directory and anonymous verification/activity links are deployed. Branch `eng/launch-acceptance` adds bounded synthetic capacity acceptance under enforced 512 MiB/0.5 CPU and strengthens CI restore from a text proof to model counts/migrations, portraits, signing fixtures, six immutable PDFs, credentials and encrypted audit, including incorrect-key rejection. Exact-head CI/review results remain pending until recorded on the PR.

Live read-only observations at approximately 13:29 UTC: service is the intended ANTHEC workspace/resource, one instance, manual deploy, 512 MiB/0.5 CPU. Current instance sample was 128688130 bytes (~122.7 MiB), CPU 0.00794 (~1.6% of limit); no error records returned. Latency series unavailable. Health endpoint returned status ok. These are light-workload observations, not capacity proof. GitHub main reported protected=false, status enforcement off, rulesets empty. No protection mutation is claimed.

Private owner-supplied policy v2 dated 2026-10-21 records internal approval by Driss Helali and an earlier local restore/decryption proof (`restore_decryption_ok`) from the hosted 16:18 UTC export. That proof covers a synthetic encrypted sample, not hosted PITR, image/PDF recovery or all key custody. The newer 23:28 UTC backup remains on the owner's Windows desktop; it has not been accessed here. Private source files stay outside this public repository.

Open gates remain distinct: actual backup/key custody and asset restore; bounded capacity result; enforced repository protection; versioned privacy notice/acknowledgements and rights/retention execution; provider/processing/transfer formalities; independent security acceptance. Do not replace missing evidence with owner authorization or technical test success. CNDP filing was previously deferred, not exempted. No paid resource, external message, production private-data mutation, DNS or Tighri change in this increment.

## 2026-10-21 — staged public preview preparation

Owner confirmed fresh backup custody and successful primary login after PR53 deployment `1487da5` (`dep-dbcbfloae00c7397l3o0`). Hosted predeploy migrated content0002–0003/governance0010–0014 successfully; initial health/login/static and anonymous-denial checks passed. No long-term stability or real-data release acceptance is inferred.

Owner authorized the next preparation increment: secure editorial-only `public-preview`, independent fail-closed application/payment/issuance guards, closed-link presentation and primary-only administration retained. See ADR034. This branch has no schema change; tests/CI/exact review remain separate evidence recorded in its PR. Current Render settings remain owner-testing; no hosted redeploy/config change, paid resource, DNS, Tighri or MHIOS change is part of this increment.

## 2026-10-12 — private Render deployment preparation

The prepared PostgreSQL disk is explicitly 1 GB with storage autoscaling disabled, matching the $13 monthly baseline; Render's larger default disk would otherwise increase cost. The revised Blueprint passes the official JSON Schema. No service or storage subscription was created.

Head `e5a02f3` passed corrected PostgreSQL/Docker/restore CI 38277825317. Exact-head review identified a Render compatibility P2: Blueprint database names may acquire a generated suffix. Runtime now validates the strict ANTHEC owner-testing namespace including an optional alphanumeric suffix and propagates the actual URL database name instead of targeting a hard-coded name. Tests cover the generated name and reject Tighri/unrelated or malformed names. Fresh final-head CI and exact review remain required.

Head `e48b72a` passed 184 PostgreSQL tests without skips, eight metadata/backup tests, Docker build and isolated restore CI 38277104832. Its external review found an additional P2: the production settings rejected the public fixture key by text rather than decoded key bytes. That check now uses a constant-time decoded-byte comparison and tests accepted whitespace variants. Final corrected-head CI and exact external review remain mandatory; no production/owner acceptance is claimed.

Initial preparation head `e93b42a` passed PostgreSQL 16 CI 38275837743 (183 application/CMS tests without skips, eight metadata/backup tests, Docker build and isolated export/encryption/restore/decryption drill). Exact-head Codex review identified two P2 findings: a generic noindex header suppressed legitimate owner locale redirects, and backup-key separation could not be checked when the data key was absent. Both are corrected with regression coverage; the corrected final head requires fresh CI and exact-head review. No release approval is inferred from the initial green CI.

Owner authorized preparation on live main `6f9c22e227334d2bf480038cd3bc3e7ccc7afa09`, after PR #23 merged. Branch `eng/private-production-readiness` preserves existing drafts, artwork, certificate wording and POL-01–08. Private settings, non-root Docker/static build, separate PG16 Blueprint, primary-only MFA gate, disabled public workflows/payments/official issuance, disabled ephemeral filesystem uploads and an offline encrypted-backup/isolated CI restore drill are prepared. See PRIVATE_DEPLOYMENT_PREPARATION.md for architecture, current public costs, domain evidence and remaining gates. Render is not connected; no resources/DNS/Tighri changes, merge, paid subscription or deployment performed. Actual ANTHEC.COM RDAP indicates an existing registration; ownership/acquisition price is unresolved. Tests, CI, exact external review, owner acceptance and live recovery are separate milestones; preparation alone does not satisfy them.

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

Package C reconciled head 385f3f9b458474237eafc5d51c39369f42cae6d0 passed PostgreSQL CI 38067775230 (121 application/CMS tests without skips, six metadata tests and required checks). Codex returned two P2 localization findings: MFA entry redirects/institutional links lost selected locale, and the professional accreditation type had no localized label. Both are corrected with validated locale propagation and printable/public verification assertions; API machine values and security rules remain unchanged. Updated-head CI/re-review required.

## 2026-10-10 — premium v4 visual direction approved; portrait package prepared

Live main re-fetched at 4962a7c3f32c16e34d08c0e7f827898cf7e9df66; no open PR. Owner explicitly approved the three reference-inspired v4 proofs. PREMIUM_DOCUMENTS.md records their design and outstanding certificate-background resolution limit without treating visual approval as print-readiness acceptance.

Package A on eng/approved-premium-portraits adds encrypted normalized portrait records, scoped member/guardian upload and administrative review, private audited image access, additive migration and portrait snapshot binding at card issuance. New uploads/reviews do not change issued cards; existing reissue commands select the current approved portrait. Legacy HTML remains unchanged; pending-photo final-PDF enforcement and templates await package B. No real-person input, deployment, external delivery or organizational decision. Local validation, exact-head PostgreSQL CI and mandatory Codex review are pending before acceptance.

Package A local validation: 133 application/CMS tests completed (121 passed, 12 PostgreSQL-only concurrency tests skipped locally); six metadata tests, standalone validator, system checks, migration drift check and pinned dependency consistency pass. These SQLite results do not establish PostgreSQL acceptance. Exact-head CI and external review remain pending.

Package A first PostgreSQL CI run 38089203835 failed on 334e7e0b15a23f480a942ba1bf08b20327a4fbfb: the preexisting 0001-to-0002 migration regression restored only 0002, removing the new portrait table before later concurrency tests. Corrected the fixture to restore the captured latest migration leaves. No schema or production behavior workaround. Updated-head PostgreSQL CI and Codex review remain required.

Corrected-head PostgreSQL CI 38089407984 passed all 133 application/CMS tests without skips plus six metadata tests. Codex review of a8c0321f4c6e918729d6c83330a74dfb9152e819 returned one P2 interface finding: photo previews showed numeric IDs while the review dropdown used UUIDs. Previews now show the same UUID as the scoped choice, with a two-person regression. Updated-head CI/re-review remain required. During this work GitHub confirmed the same repository ID 1413200545 was renamed externally to asccof/ANTHEC; subsequent API requests use the new canonical path, with internal module names unchanged.

Second updated-head Codex review of 7ef300f91a6942e5e1fc73706815374643c2e1f7 identified the remaining >100-row boundary: form choices included portraits outside the first 100 previews. Both now use the same ordered, capped identifier set. A 102-portrait regression verifies exact alignment and rejects a hidden choice. Updated-head CI/review remain required.

## 2026-10-10 — premium portraits accepted; PDF package prepared

PR #21 final head 0a33fa7c9678654d44b7f525b8d81cd2806d4879 passed PostgreSQL 16 CI 38090250852 and exact-head Codex review without major issues. Both portrait-choice mapping findings are resolved with regressions, including the 102-row boundary. Merged main: 9723bc215ad9ea215ec6bccd3f496ce9c801de29. Current canonical repository is asccof/ANTHEC, same repository ID/history.

Package B adds immutable encrypted language-specific PDF artifacts, existing outbox integration, protected preview/read-only download and POST/CSRF generation, multilingual CR80 and A4 templates, and synthetic journey/concurrency regressions. Approved gold/president artwork and original logo are reused. The low-resolution certificate ornament is reconstructed as self-contained vector curves; no missing photographic detail or physical print approval is claimed. Remaining card palettes share one composition and existing domain categories; participation issuance is intentionally absent pending an owner-approved eligibility contract. All generated PDFs remain visibly SPECIMEN in this synthetic-only implementation. No production deployment, real records, signatures/seals, policy changes or external delivery.

Package B local validation and updated-head PostgreSQL CI/Codex review are pending; this preparation entry is not acceptance.

Package B first head c6843d124b77063fa149e15bc41f0df72e74fe0e passed PostgreSQL 16 CI 38090808868 (148 application/CMS tests without skips plus six metadata tests). Codex returned two P2 findings: lifecycle state was not rechecked under origin/document locks during PDF generation, and the asset provenance conflated the Python distribution version with the embedded SVG generator label. Both are corrected with stale-state/outbox and real PostgreSQL revocation-lock regressions. Independent nine-PDF print checks passed exact page sizes, embedded fonts, text page bounds and 18 ZXing QR decodes at 300/600 DPI; physical printing remains unverified. Self-review also improved gold-header contrast and corrected the legacy HTML acronym, without modifying existing artifacts. Updated-head CI and exact-head review remain required.

Second package B head 2f48d0d7263b93e484e74d8c0eb15c77144651fe passed PostgreSQL 16 CI 38091239227 (150 tests without skips). Codex identified one remaining P2 delivery race: unlocked preview/download reads could precede an uncommitted lifecycle change. Generation and delivery now share document/origin locking; HTTP views retain transaction locks through audit/response construction, acquiring administrative authority first to match command order. A PostgreSQL HTTP regression verifies both download and preview wait for origin termination and return 410 while preserving the artifact. Updated-head CI and exact-head review remain required.

Third package B head a40603b1e42ab86ad1fe07fc0de7d16e1df51e21 passed PostgreSQL 16 CI 38091611248 (151 tests without skips). Codex found a P2 conservative early-rejection race in POST generation during suspended-to-active reactivation. Removed the unlocked early status check; artifact_for is now the single locked lifecycle decision. A CSRF-enforced PostgreSQL HTTP regression verifies generation waits for committed reactivation and succeeds. Updated-head CI and exact-head review remain required.

Fourth package B head c5475eea502908df3af48c856a37683201b45ac5 passed PostgreSQL 16 CI 38091891033 (152 tests without skips). Codex found a P2 outbox-completion gap: inactive jobs were marked rendered, preventing automatic retry after valid reactivation. Inactive PDF work now remains failed/retryable through the existing worker; completed legacy HTML and existing PDF artifacts are preserved. A worker regression suspends, retries after activation, prepares all three languages, and verifies replay/history. The complete synthetic design catalogue contains 30 PDFs across eight existing card categories and two supported certificate types in AR/FR/EN; independent checks passed page dimensions/fonts/text bounds and 60 QR decodes at 300/600 DPI. Updated-head CI/review remain required.

Fifth package B head 5957df35a03dcd1296abe80f626366d637ae79fd passed PostgreSQL 16 CI 38092286474 (153 tests without skips). Codex identified the terminal-job starvation boundary. Existing lifecycle rules now classify inactive work under the same document/origin locks: void/expired/terminated and irreversible cancelled offices retire; reversible membership/accreditation/founder/suspension cases remain retryable. This is worker bookkeeping, not a new membership/office state or policy. Retired jobs are excluded and retry ordering rotates by attempts/PK. Regressions cover 100 terminal rows followed by new issuance and existing cancelled-founder reactivation rules.

Print self-review preserves original artwork geometry inside the trim when adding bleed and preserves the original logo aspect ratio. New issue timestamps are captured at issuance, distinct from effective validity (early renewal); migration leaves historic timestamps NULL rather than guessing. Certificate labels show both actual recorded issue date and the effective term. Updated final-head PostgreSQL CI and exact-head review remain required.

Sixth package B head 5d15ebca64616e81556a27e0ae1cad4a293645a9 is reviewed with one P2 lock-order finding around membership-linked accreditation state updates. The existing right.state command now explicitly acquires linked membership before accreditation, matching PDF generation/delivery and membership-state propagation; its state validation/audit rules are unchanged. A PostgreSQL regression holds membership, proves the state worker has not acquired accreditation, renders concurrently, then verifies the committed suspension without deadlock or lost history. Updated-head PostgreSQL CI and exact-head review remain required.


## 2026-10-11 - focused credential redesign, owner review pending

Starting live main: 6b6ab8d43d68abcd079caed2a2edf684dd4925b8 (PRs #21/#22 merged). Owner authorized focused visual redesign and review, explicitly excluding merge/deployment and participation issuance. Existing local drafts are preserved in separate directories; the bounded branch is eng/credential-visual-refinement. President artwork and original logo remain unchanged. Seven category compositions and both certificate designs are refined; general display labels change only to عضو / Membre / Member. Full references move off card fronts. Certificate subtype/issue date/effective dates follow existing records. Participation is a separately marked pure visual proof with NOT ISSUED reference and non-operational QR; no issuance/model/route is added. Proposed English institutional wording needs owner content approval.

Targeted local PDF tests: 19 pass; six baseline tests and standalone validator pass; Django checks and migration drift are clean. Full final-head application tests, PostgreSQL CI, independent all-language PDF/QR/font checks and Codex review are pending at this preparation entry. Evidence will be recorded in the draft PR and owner report rather than inferred from an earlier head. Visual acceptance and physical printing are still pending. See VISUAL_REDESIGN_REVIEW.md for exact scope, data mapping and limits. No merge or deployment.


Draft PR #23 initial head f07fb55065f25a28e135b1631d33eb282e725e49 passed PostgreSQL CI run 38161419173 and exact-head Codex review without major findings. Local complete suite: 160 tests, 18 PostgreSQL-only skips on SQLite; all executed tests pass. Initial independent proof set passed 33 PDF dimensions/font/page-bound checks and 99 digital QR decodes (MuPDF 300/600 DPI and Poppler 300 DPI). Visual inspection then found a Vice-President bottom border crossing the validity/footer and a President validity label crossing the gold ribbon. Their geometry/text positions are corrected; duplicate hidden instruction text is removed. Updated-head CI/Codex review and regenerated proofs are required. These corrections are visual QA, not final owner approval.


Head 5c7281bd2197a6daf8b46589614bae8d6322ffde passed PostgreSQL 16 CI 38161729127 (160 application/CMS tests without skips; metadata/system/migration/dependency checks pass) and exact-head Codex review without major findings. Independent regenerated 33-PDF checks again passed dimensions, embedded fonts, text page bounds and 99 digital QR decodes. Final cross-renderer visual comparison exposed a decoration-only difference: SVG gradient-painted leaves/frame details appear filled in MuPDF but partly outlined in Poppler. New vector decoration therefore uses fixed gold paint with explicit highlight veins; the original President raster is unchanged. Updated-head CI/review and cross-renderer proof regeneration remain required before delivery. Physical foil/CMYK approval is not implied.


## 2026-10-12 - final color/content/signing refinement of draft PR #23

Verified main 6b6ab8d43d68abcd079caed2a2edf684dd4925b8 and draft head c62110ab6272f593e13faa8bbaec0b35e53c31a3. Owner accepts the artistic direction and authorizes dominant affiliate #145B67 / advanced #49345F fields, final certificate content and authentic presidential signature/stamp integration. Official signatory text is [owner-approved Arabic identity in private configuration] / [owner-approved Latin identity in private configuration]. English institutional denomination remains proposed. Other approved artwork is preserved; general display labels and business rules are unchanged.

Added primary-only encrypted reviewed artwork and additive immutable document signing snapshots using existing POL-04 authority/MFA/re-auth/command/audit controls. No new authorization policy or participation model/route/issuance. Actual images are still pending; proofs carry explicit placeholders and NOT ISSUED participation QR. New unsigned certificate artifact generation fails closed; existing PDF artifacts are not rewritten. Replacements require existing formal reissuance. Professional criteria-fulfillment wording is limited because the current approved schema has no independent assessment finding or detailed scope field. See CERTIFICATE_SIGNATURE_REFINEMENT.md.

Local full suite before the final HTTP-upload regression: 165 tests pass with 18 PostgreSQL-only skips; 19 PDF regressions pass; metadata validator and six tests, Django checks and migration drift pass. Updated complete PostgreSQL CI and exact-head Codex review remain pending at this preparation entry. This is prepared/tested work, not visual approval, deployment or merge.


Initial signing-refinement head 986cf7d3acb6a224b83f7701709384ebf999c4d3 passed PostgreSQL CI 38228323455. Codex found a P1 unsigned-HTML bypass: credential-bearing legacy HTML could be downloaded even when PDF generation required approved assets. Certificate HTML is now a non-credential notice without identifiers/codes/tokens, its download route redirects to protected PDF, and missing-assets outbox work remains failed/pending_assets. Archived HTML/PDF bytes are preserved. Added a holder HTTP/worker regression proving 409 with no unsigned credential delivery. Updated-head CI/Codex review required.


The same signed-edition gate also covers cached legacy certificate PDF delivery/replay: approved captured asset pairs and matching signing metadata are required. Historical unsigned bytes remain archived unchanged, with explicit marked preview and formal reissuance for adoption. Added a legacy PDF regression proving 409 before/after asset replacement, 200 marked preview and unchanged archived payload. No membership/accreditation status or public verification policy change.


Codex review of d7899ebc43850da8071dda7f1f34d0833ecd76b8 identified a P2 permanent-retry gap for immutable missing signing snapshots. Those jobs now retire with pending_assets diagnostics, preserving records while excluding them from later worker batches; formal reissuance creates new work. Added the 100-old-jobs boundary regression. PostgreSQL run 38229756099 also exposed an older journey expectation of credential-bearing certificate HTML; the regression now verifies protected-PDF redirect and 409 pending assets while preserving the existing public verification/renewal checks. Updated-head CI/Codex evidence is required.


Head 36b6e483b28ad538640ece6806c6b93f87e98d6a passed PostgreSQL CI 38231258660. Codex identified actual signatory text in public source contrary to AGENTS data boundaries. Identity now comes from protected owner-provided runtime configuration and is captured immutably; public tests use synthetic identity, while private owner proofs must retain the approved actual spelling. Updated-head CI/Codex required. The local execution environment disconnected before this correction; remote edits continue with exact-head leases, and refreshed private proof/report rendering and persistent delivery remain pending until the environment reconnects. No history rewrite, merge, deployment or participation activation.


## 2026-10-12 - certificate typography only / draft PR #23

Owner accepts card artistic direction in principle; final certificate visual acceptance remains pending. Continue verified 55b855a7ad5c6353cfd297004ccfc4c50a6ea47d without changing approved card artwork, content, fees, validity, permissions or issuance. Increased certificate body/legal/holder/reference/date sizes, tightened central spacing and aligned QR/signature/stamp areas; preserved authentic-asset pending state and pure NOT ISSUED participation proofs. New certificate template version is recorded on new artifacts; cached historical bytes and card version remain unchanged.

Baseline metadata validator, six metadata tests, Django checks and migration drift pass locally. Initial focused PDF/asset/access/journey suite: 44 tests pass with six PostgreSQL-only skips on SQLite; final four layout tests pass after the added bounded typography guard. Full PostgreSQL CI and exact-head Codex review for this follow-up remain pending at drafting; their final evidence belongs in PR #23 and the owner report. This is not final visual approval or physical print certification. No merge, deployment or production/participation activation.

Codex reviewed interim typography head d79e6687a2 without major findings. The requested exact-head review after the QR-caption placement correction was rejected by the Codex review usage limit. A subsequent self-check found and fixed sizing of the unsigned missing-identity notice; all four final layout regressions pass. The final head still requires external Codex review when that service limit is restored; neither the earlier review nor successful CI constitutes that final review or owner visual acceptance.


## 2026-10-13 — Render login throttle follow-up

PR #24 is merged at 4f74340aede020a972c4924f01d09ff20e7b247d. The owner verified the isolated ANTHEC workspace tea-db6humt9fdbs73fj7jk0 is Hobby and approved the $13/month base web/PostgreSQL resources and private synthetic deployment, before taxes/overages. Tighri remains protected. No resource has been created or deployed during this follow-up.

A later Codex review (5494442282, posted after the merge) identified the shared Render ingress REMOTE_ADDR login bucket as an availability issue. This bounded branch removes that unintended ten-attempt peer ceiling, retains the explicit global fifty-attempt/five-minute ceiling without trusting forwarding headers, and moves counting to process_view after CSRF validation. Regressions use the full CSRF-enforcing client stack for shared-peer/header rotation and invalid-CSRF flood cases. Global-budget exhaustion by CSRF-valid traffic remains a rate-limiting availability tradeoff; this change does not claim DDoS immunity.

Local validation passed: thirteen focused deployment tests on SQLite, eight metadata/backup tests, metadata validator, Django checks and migration drift. Fresh PostgreSQL CI and exact-head Codex review remain pending; SQLite is not PostgreSQL compatibility evidence. The follow-up requires owner merge approval; existing financial authorization is preserved. No design, policy, credential lifecycle, real data or issuance change.


## 2026-10-13 — first Render deployment / static permission correction

The owner approved merging PR #25 and corrected Render pricing of $13.30/month before taxes/overages. Main b4b3751d8e26734a11b85ccd1b155e0de03de740 was deployed only into ANTHEC workspace tea-db6humt9fdbs73fj7jk0. Blueprint exs-db75o26i0phs738ls570 created dedicated web srv-db75roid0e5s73b5tg50 and PG16 dpg-db75r3id0e5s73b5r7u0-a (1 GB, autoscaling off, empty external allowlist). Unique keys were set privately in Render. Web auto-deploy/previews and Blueprint Auto Sync are off. No Tighri mutation or real/private asset import.

First deploy dep-db75rpad0e5s73b5tii0 built successfully but failed before migrations/startup: PermissionError reading /app/staticfiles/staticfiles.json as UID/GID 10001. The bounded correction grants read/traverse access only to collected public static assets, retains the non-root runtime and protected upload restrictions, and adds an offline final-image smoke check for production startup, manifest and every hashed asset. Full CI/exact-head Codex review and separate owner merge approval remain required. Resources exist and may accrue the approved cost; the website and primary account are not yet live or ready for owner testing.


## 2026-10-13 — Render pre-deploy command execution correction

PR #26 merged with owner approval at ff127927b38338cfbde5f725f3fcd12bba66bdbe. The final image's static permissions are corrected. Actual Render Docker pre-deploy execution treated the combined check/migrate string as one command's arguments; explicit single/double quoted shell variants also failed. No migration or live owner-ready deployment is claimed.

This bounded follow-up replaces platform shell parsing with python deploy/predeploy.py. The script invokes each management command with a separate argument array, preserves check --deploy --fail-level ERROR before migrate --noinput, and stops on any failure. PostgreSQL CI now executes this exact entry point. No policies, assets, domain models, security settings or schema changes. The two previously approved ANTHEC resources remain isolated at $13.30/month base; auto-deploy/Blueprint Sync remain off, no Tighri changes or real data. Tests, exact-head review and owner merge approval are required before this new file can be deployed from main.


## 2026-10-14 — honorary institutional path and return navigation (prepared)

Owner authorized the honorary designation and localized return links on 2026-10-14. The bounded change extends permanent institutional designations to honorary members under POL-01/03, without annual renewal, payment or automatic professional accreditation. Existing honorary membership records are not migrated or relabeled. A separate honorary card uses the existing approved honorary artwork; database uniqueness and permanent-term constraints apply. Grant/reissue retains the issuance guard and is unavailable in owner-testing. No actual designation/document is seeded by this change.

Shared HTML navigation returns to the protected locale-specific website and, for staff, administration. Wagtail receives a return-to-site menu item. Owner-testing, MFA, registration/payment/issuance blocks and all approved assets are preserved. No Tighri changes, paid resources or plan changes. Local validation and external exact-head CI/review are distinct; no merge/deployment of this increment is claimed here until verified.

Private acceptance of the prior deployed version: owner successfully enrolled MFA and opened administration; the MFA rejection was traced to a one-hour device-clock offset. Six synthetic application fixtures were loaded by the owner, and owner reported successful detail/language/rejection testing. Historical OOM allocation source remains unproven; it must not be described as fixed by these interface changes.


## 2026-10-14 — partnership workflow and completeness reconciliation (prepared)

Owner authorized the completeness review and ordered remaining implementation on 2026-10-14. COMPLETENESS_REVIEW.md records accepted evidence separately from actual live owner testing, disabled functions and remaining gates; historical documentation now links to it. This increment adds private partnership requests/decisions, hidden partner records and manual localized content/visibility/state management with audit and recent MFA authorization. Owner-testing public submissions/publication stay blocked; no email, fee, membership/accreditation or issuance side effects. A manually run idempotent command prepares three synthetic requests; it is not run during deployment. Branch governance and the other listed interfaces remain separate unfinished increments. Tests, exact-head PostgreSQL/container CI and Codex review are required before merge/deployment; no new acceptance is claimed by this preparation note.

## 2026-10-14 — independent assessment UI prepared (not yet accepted)

Owner accepted the private partnership test and authorized independent accreditation casework followed by event interfaces. Branch `eng/accreditation-review-ui` adds an administrative-only independent assessment register and encrypted private criteria/notes/optional internal quote. No actual organizational criteria or fees are supplied or invented. Draft/review/rejection does not grant rights; final approval reuses existing atomic issuance and replay protection. Owner-testing blocks final issuance, including forged POSTs. No public case API, file upload, external delivery, payment or membership grant is added. Three synthetic case fixtures require a manual guarded command. Event interfaces remain a separate next increment. Nine targeted synthetic case tests passed; exact-head external review, PostgreSQL CI and deployment remain pending at preparation.

## 2026-10-14 — independent casework reviewed; event UI prepared

PR32 exact head 958b5f4e0bf5c5c19645e35c8fea47e56adeda86 passed PostgreSQL/container/recovery CI 38591564343 and completed Codex review without findings (15:45:49Z). Owner authorized merge/private deployment; merged main 289c376e65a94554a41fa34aaf04675c6157281a. Render deployment dep-db7q8bdg1s2s73bfe0o0 was triggered, success/owner acceptance still pending at preparation. Local full suite 208 passed with 18 PostgreSQL-only skips; final added HTTP/history test separately passed in nine-case targeted suite.

Branch eng/events-management-ui prepares activity configuration, participation/guardian forms, admission decisions and attendance interfaces. Existing conditions are protected after requests, current conditions locked during registration, capacity and invitation validity preserved. Nine targeted synthetic interface tests passed. Requests/invitations remain blocked in owner-testing; manual seed_activity_demo creates two synthetic pending requests and an unusable-password nonstaff synthetic participant account, never a document/payment. Exact-head review/CI/deployment and owner acceptance are pending. Actual consent templates/event conditions, file evidence, real hosting invitation/attendance acceptance and legal/security readiness remain unfinished.

Final local event increment suite: 218 tests passed, with 18 PostgreSQL-only skips. Follow-up privacy assertion ensures the independent case final approval reason remains encrypted rather than copied to the shared plaintext accreditation audit; targeted case/activity tests cover the final change. Exact-head CI/review still required.


## 2026-10-15 — PR33 accepted; operational director/pricing screens prepared

Owner reports successful private activity/request test after PR33 deployment b0132b0c08ed087dcd6c07da8cf4da2361023d9b, CI 38593183235 and completed Codex review. Issued invitation/attendance remains untested live because issuance is disabled. Owner explicitly authorizes director/pricing interfaces followed by multilingual public presentation.

Branch eng/directors-pricing-ui prepares primary-only director management and prospective versioned price changes using existing commands, explicit confirmation and recent MFA. Protected primary/superuser targets excluded; revoked epochs remain invalid; old quotes are unchanged. Optional price decision reason is audited. No prices or privileges change at deployment. Manual seed_operations_demo creates one unusable-password, unprivileged synthetic candidate only.

Local execution is unavailable due environment connection failure. No local test pass is claimed. New synthetic acceptance tests and all existing metadata/system/drift/PostgreSQL/recovery/container checks must pass CI, followed by exact-head Codex review before authorized private deployment. Public site work follows in a separate bounded increment. No launch, delivery, real-person data, plan/resource or Tighri change.

PR34 review found an active-target requirement enforced only in the view. Follow-up moves that validation into the existing locked delegation service, removes the stale view check and adds direct-service/JSON rejection plus inactive revocation regression coverage. No local pass claimed; final-head CI/review required.


## 2026-10-15 — multilingual presentation prepared (stacked after PR34)

Owner authorizes the public-facing presentation as the next private-test increment. Branch eng/multilingual-presentation stacks after the reviewed director/pricing work; it must not merge before PR34 is accepted by CI/review and merged. No owner acceptance of either new interface is assumed.

Prepared responsive navy/gold/teal AR/FR/EN landing sections and semantic navigation, corrected ANTHEC wordmark, effective public membership prices, accreditation rule summaries, activities/partner entry points and privacy/trial notices. Existing CMS records and card/certificate artwork remain unchanged. Public prices exclude future/free-designation overrides and all internal accreditation fees or application quotes. Owner-testing hides signup action and preserves the anonymous gate.

Six new synthetic presentation tests cover localized sections, active public price scope, private record exclusion, trial gates, editable child pages and absent-price behavior. Existing CMS revision/translation/draft/XSS tests remain authoritative. Local environment is unavailable: no local pass or visual screenshot claimed. Exact-head PostgreSQL CI/recovery/container and Codex review required before private publication; desktop/mobile/language owner acceptance follows. Final editorial/contact/legal content and readiness remain pending.


## 2026-10-15 — accepted operational UI; integrated readiness review

Owner reports successful PR34/35 directors/pricing and AR/FR/EN presentation testing, then explicitly authorizes comprehensive review. Accepted baseline main eaea9cd311106624d05a12c0448cac07634f74bc, tree 49a1d13e68cbc36e286fa2ca0a697e40e9f8889b; CI 38748300592/38748480548, completed Codex reviews, private Render dep-db8dv22j9qps73cj5j30. Active g9djk memory ~117.3–124.8 MiB and no error/failure/restart records through 14:40Z; historical OOM allocator remains unknown.

Branch eng/integrated-readiness-review adds joined synthetic case→signed PDF→verification→state/reissue, guest/guardian→invitation→attendance/cancellation and owner-only cross-domain guard tests. Three joined tests passed on baseline; two independent annual-date regressions failed, proving a delayed approval could retain an old proposed term. POL-02 correction anchors individual/institution annual validity at final approval, preserves course dates and proposed/effective audit history, and explains the rule in AR/FR/EN. No old rights/artifacts are rewritten and hosted issuance stays blocked.

RELEASE_READINESS_REVIEW.md separates automated/owner/hosted/unverified evidence and identifies FR/EN invitation-output, hosted issuance/restore/key/capacity, final content, legal/security and scope gaps. This is not launch authority. Final local checks, PostgreSQL CI and exact-head Codex review are pending at preparation. No paid resource/plan, real-person data, delivery, DNS or Tighri changes.

Local review checks completed: 238 content/governance tests passed (18 PostgreSQL-only skips), 10 metadata tests passed, and final targeted 14 case/joined tests passed after history display/replacement-date checks. Metadata validator, Django checks, migration drift, dependency and diff checks passed. Exact-head PostgreSQL CI and Codex review remain pending; this does not close hosted/operational/legal gates.


## 2026-10-15 — invitation output localization prepared

Owner authorizes continuation after PR36. Baseline main fe1ab064da0300bd3be57e56177be64116e1766c passed CI 38756044296 (238 PostgreSQL domain/content tests, 10 metadata tests), completed Codex review and private deployment dep-db8en17avr4c73b7ecc0. Branch eng/invitation-localization replaces the Arabic-only invitation HTML fallback with AR/FR/EN allowlisted field/status labels, explicit inclusive last-day wording and language-preserving verification QR links with secrets only in the fragment. Machine verification vocabulary, identity snapshot, lifecycle/access rules, card/certificate artwork and participation proof are unchanged. Synthetic tests exercise guardian download, escaping/private-data exclusion, current status after rendering, inclusive expiry, replacement and QR semantics. Final local checks, PostgreSQL CI and exact-head Codex review are pending. Evidence/authorized private deployment receipt will be recorded in the PR without modifying the tested tree. Hosted issuance/registration/payment gates, plan/resources and Tighri remain unchanged.

PR37 initial local suite passed 241 tests (18 PostgreSQL-only skips), plus all metadata/system/drift/dependency checks. Codex identified the inherited institutional role label on invitation type; the follow-up adds an invitation-specific AR/FR/EN type label and literal output assertions. Final-head CI and re-review are required.

PR37 re-review identified that invitation QR browser results still fell back to machine JSON. Follow-up selects invitation vocabulary for HTML-accepting verification requests, preserving explicit JSON responses; synthetic CSRF browser tests cover AR/FR/EN allowlisted/escaped results, cancellation and unchanged machine contract. Final-head validation and re-review remain required.


## 2026-10-15 — owner acceptance and recovery/security package prepared

Owner explicitly authorizes preparation after PR37. Baseline main 65a0613a5814c65316a6ff25497e53e58a2a523a, tested tree c98669f62a5ce54e69d8585b6ff5b3882eaabe07; CI 38760258404 passed 242 PostgreSQL tests +10 metadata, container and synthetic encrypted recovery; final Codex review +1 and both findings resolved. Private dep-db8f4e6q1p3s73ak36t0 live 15:34:17Z, seven post-live checks passed, ~121.24–121.25 MiB samples through 15:35:47Z. No hosted issuance/restore/capacity or historical OOM allocator proof.

Branch eng/owner-acceptance-recovery prepares Arabic twelve-scenario owner acceptance and recovery/security runbook, reconciles closed PR36/37 engineering gaps in the current registers, and adds read-only check_owner_readiness. The shell command is owner-testing-only, uses PostgreSQL READ ONLY, returns allowlisted booleans without secrets/identity, performs no repairs or key/MFA changes and always reports release_authorized=false. Three synthetic command tests initially passed locally. Final full local/PostgreSQL CI and exact-head Codex review remain required; evidence/authorized private deployment receipt will be recorded in the PR.

Scoped Render DB metadata: PostgreSQL16 available, 0.1c-256mb /1GB, external IP allowlist empty; read-only SQL connector cannot reach it, so live authority/MFA rows remain unverified. No allowlist changes. Official Render recovery documentation checked 2026-10-15; actual available backup window/exports were not inspected. Key possession, off-provider retention/RPO/RTO, real restore, load and independent legal/security decisions remain open. No new paid/local hosted resources, connection cutover, issuance/payment/application changes, delivery, DNS or Tighri change.

PR38 initial full local suite passed 245 tests (18 PostgreSQL-only skips), metadata10/system/drift/pip/diff and package links passed. Codex identified the general 100 MAD annual membership missing from UAT-05; corrected to include all four annual categories and explicitly exclude automatic accreditation for general/affiliate/advanced. No runtime or policy change. Final-head CI and re-review required.

## 2026-10-16 — owner-approved member intake and verification correction prepared

Baseline main 1fa6d72c8b8c56f06c8474e951c8a6fdfde5fefd (PR38). Owner approves separate declared applicant capacity (including therapeutic coach, psychological guide/counsellor), private phone and profession/study field, and action-specific AR/FR/EN form captions. ADR-021 records schema/backward compatibility, privacy, immutable application declarations and pending evidence. Verification form referrer policy corrected to same-origin without disabling CSRF. Local owner UAT verified active replacement/cancelled old card, lifecycle state and early renewal; slow local responses remain explicitly deferred and unresolved. New intake owner testing, PostgreSQL CI, exact-head review and deployment are not yet accepted. No real data, paid resources, plan changes, hosted gate relaxation, Tighri or MHIOS changes.

Initial focused suite passed 22 tests, metadata validator and 10 metadata tests passed, Django system/migration-drift and dependency checks passed. Full local suite and PostgreSQL CI are pending; no full-suite pass is claimed yet. Browser probe automation was unavailable because this environment has no installed Chromium binary; the owner's actual local-browser correction result and CSRF middleware positive/negative tests are recorded separately.

PR39 Codex identified a migrated-profile bypass: an existing account could apply without completing blank new phone/profession fields. Follow-up enforces completion at browser and command boundaries, preserving legacy blank-compatible renewals, with a regression test. New-head checks/re-review required.


## 2026-10-16 — application portrait and private addresses

Owner authorized portrait upload at application time plus correspondence/professional addresses for professionals and residential address only for beneficiaries. Bounded implementation and regression coverage prepared on eng/application-photo-addresses from main 603a074; see ADR-022. New self-service approval waits for accepted application portrait, with atomic upload and protected first issuance. Existing requests/renewals and issued snapshots remain compatible. CI, review, merge, local owner acceptance and deployment are separate milestones, not implied by preparation. Private host gates/costs and Tighri untouched.

## 2026-10-17 — homepage content and association structure

Owner local synthetic UAT reported successful application photo/address branches and approval guard, accredited multilingual signed specimen certificate and verification, accredited renewal, honorary/founder permanence, cross-member PDF 404, exemption, bounded refund, rejection/resubmission and portrait replacement. These are owner-observed local results; they do not establish hosted performance, legal/security release acceptance or complete all event/institutional UAT. The owner explicitly moved to page content/design and kept latency deferred.

Homepage increment prepared from main 8a74d41 on eng/homepage-mission-services: mission/goals, beneficiary/professional services, local Arabic fonts and existing logo, editable explicitly published leadership names, responsive public presentation, with existing policies and private hosting gates preserved. See ADR-023. Approved names/localized spelling, owner desktop/mobile acceptance, final CI/review and deployment remain separate pending milestones. Member/admin redesign is a later bounded increment.

## 2026-10-17 — editable public contact

Owner supplied association telephone/WhatsApp and Rabat address for display, and approved editable contact settings plus a blank official email placeholder. Prepared homepage contact section and institutional footer with localized headings/addresses, one phone feeding both call and WhatsApp, and Wagtail administration settings. No account/profile contact is queried; owner-authorized public contact is separate from synthetic UAT identity data. See ADR-024. Exact-head CI/review, owner local visual acceptance and deployment remain distinct pending milestones. No resource/cost or trial gate changes.

## 2026-10-17 — private member dashboard presentation

Owner confirmed local public contact update and explicit Arabic/Latin leadership publication in three homepage locales using a revision-preserving local content command; seven founders are displayed, with president and vice-president/treasurer. This is CMS content acceptance, not creation of accounts, memberships or accreditation decisions.

Prepared member-home dashboard from main b2cf93b on eng/member-dashboard-presentation: own membership periods/states, private pending/document totals, application cards and profile/portrait/renewal quick access with shared private styling. Existing permissions/financial/document rules and private gates remain unchanged. See ADR-025. Focused 21 account/dashboard/journey tests passed locally; full CI/review and owner desktop/mobile acceptance are pending. Local latency remains deferred; no hosting, paid resource, Tighri or MHIOS changes.

### 2026-10-18 — membership operations presentation preparation

Owner accepted the member dashboard and supplied current administration screenshots. Prepared localized request cards, financial summaries, grouped decision forms and explicit command captions. Existing authorization, recent MFA, CSRF, financial and portrait prerequisites, audit history and document ownership remain in the existing services. No migration or hosted deployment. Required local checks, PostgreSQL CI and exact-head external review are pending; final evidence belongs in the PR. Owner visual acceptance of this increment is pending.

### 2026-10-18 — institutional card presentation preparation

Owner accepted membership administration presentation and authorized continuing. Prepared consistent institutional header/navigation, responsive register cards, explicit recorded role state and term dates, separate issued card status/actions and grouped decision forms/history. No schema, policy, artwork or hosted deployment changes. Local checks, PostgreSQL/container/recovery CI and exact-head review pending; final evidence belongs in the PR. Owner visual acceptance pending.

### 2026-10-18 — private asset review presentation preparation

Owner accepted institutional card presentation and authorized portrait/signature/stamp interface work. Prepared responsive private galleries, reference/state/date facts, clearer upload/review instructions and identifiable selector captions. Existing queue windows, pending-only decisions, authority, recent MFA, CSRF and immutable document assets preserved. No schema, artwork, hosting or release changes. Required tests/CI/review and owner visual acceptance pending; final evidence belongs in the PR. Lazy previews do not establish a fix for deferred server latency.

### 2026-10-18 — explicit per-action delegation preparation

Owner authorized independent view/action checkboxes rather than broad operational delegation. Prepared the closed capability catalog, transactional command checks, scoped reads/private media/documents, mixed-domain data redaction, per-account CMS groups and fail-closed admin route adapter. Signing asset access is now explicitly delegatable; primary identity, delegation management and technical/user/security administration remain primary-only. Saved-draft publication is independent from draft editing; compound changes require all affected action scopes.

Migration 0012 disables legacy broad grants, increments session epochs and removes the shared CMS group; primary authority is unchanged. Legacy delegates need explicit reassignment and reauthentication. Director forms load the selected account, show grouped independent scopes and prerequisites, require reason/confirmation and reject stale edits. Before/after grants are audited. Final full tests, PostgreSQL/container/recovery CI, exact-head review and owner visual/delegated-login acceptance are pending; final evidence belongs in the PR. No hosted deployment, paid resources, public signup/payment/release changes, or Tighri modifications.


## 2026-10-19 — owner-approved login/session policy amendment

Following PR #47 scoped capabilities, the owner authorized password-only delegated login and primary MFA only at login, without operation-time reauthentication. ADR 030 records the POL-04 amendment, actual-login epoch binding, unchanged server-side scopes/revocation and shared administrative workspace navigation. Implementation prepared on eng/login-only-mfa; local/full PostgreSQL/container/recovery CI, exact-head review and owner UAT must be recorded separately. No hosted deploy, resource change, Tighri modification or public-release approval.

## 2026-10-19 — public activity editorial authoring

Owner accepted PR48 login/delegation changes locally, then deferred latency work and authorized activity public presentation linked to administrative content/media authoring. ADR031 records bounded AR/FR/EN editorial content, visible/past catalogs, normalized PostgreSQL activity images, named HTTPS/video links, explicit publication/media scopes and unchanged participation/owner-testing gates. Migration0013 keeps existing activities hidden in the new public catalog until explicitly completed and shown. Initial 36 activity/editorial/scope tests passed locally; full suite, PostgreSQL/container/recovery CI and exact-head review are separate pending evidence. Owner desktop/mobile/editorial UAT remains pending. No Tighri, paid resource, hosting, private document artwork or release change.

## 2026-10-19 — visible activity edit entry points

Owner reported successful activity UAT but could not find editing after publication. The existing administrative editor and transactional live-edit permissions remain; explicit localized edit links are prepared on public catalog/detail and administrative cards, pointing directly to the editor. Links follow current activity.edit and, for visible records, activity.publish grants; primary retains full verified-session access. Published descriptions and frozen participant conditions remain enforced. HTTP regression covers anonymous/view-only/edit-only/authorized delegated access and live saving. Local checks, full PostgreSQL/container/recovery CI, exact-head review and owner confirmation of this correction remain separate evidence in the PR. No hosted deployment or Tighri changes.

## 2026-10-19 — optional free-tier activity translation preparation

Owner accepted PR50 editing fix, clarified automatic publisher translation, and approved optional free Gemini translation for public editorial content. ADR032 records the scope amendment, explicit preview/direct-publish/accept choices, protected manual target text, private-data exclusion, bounded fixed provider, durable daily cap/cache, pre/post-network authorization and default-disabled setup. Migration0014 adds TranslationAttempt. No live key/call/quality verification, billing activation, deployment or Tighri change. Local mocked tests, required PostgreSQL/container/recovery CI, exact-head review and owner real-key UAT are distinct evidence to record in the PR.

## 2026-10-20 — public document verification entry point

Owner reported successful local Gemini translation testing, then noted that the website had no visible document-verification entry. Prepared a shared AR/FR/EN link to the existing document_verify route with the selected locale, visible in the institutional header/footer, homepage hero and public activity navigation. Existing responsive button/navigation styles are reused. In hosted owner-testing, where middleware intentionally blocks /verify/, the shared control is an explicitly disabled labelled span rather than a dead link; local development retains the active link. No verification logic, document data, reference/code requirements, CSRF, rate limits or owner-testing gate changes; no hosted deployment, paid resources or Tighri changes. Content/system/migration/metadata checks, full CI and exact-head review are separate PR evidence. Owner visual acceptance of this link remains pending.

## 2026-10-21 — remaining presentation and current closure register

Owner requested continuing the remaining work. ADR033 prepares public partners/proposal and verification form/result/error presentation, private partnership register/review/edit and independent accreditation presentation, with preserved scopes/private projections/CSRF/trial gates and stable machine verification responses. Browser invalid/throttled verification returns localized non-reflecting HTML at existing404/429 statuses. CURRENT_COMPLETION_AR.md replaces stale assumptions with exact PR52 baseline, owner-reported local acceptance, current correction UAT, unresolved latency/OOM/restore/legal/repository controls and explicitly incomplete original feature areas. No hosted deployment, resource/price increase, payment/email activation, branch policy, private file upload or Tighri changes. Required checks/CI/exact-head review and owner visual acceptance remain distinct PR evidence.


## 2026-10-21 operational release preparation

Owner requests continued engineering toward full operational launch; CNDP filing is explicitly deferred, not evidenced as exempt or completed. ADR035 adds an independently acknowledged operational runtime with off-by-default application/payment/issuance switches, secure existing settings, protected administration, and a sanitized read-only release observation command. This is code preparation, not live activation. No Render environment, database, plan, external delivery or Tighri change. PostgreSQL CI and exact-head review remain pending until evidenced in the PR.

Owner reports successful actual Render export/local restore of one encrypted synthetic audit canary and `restore_decryption_ok` with the saved original key. This proves that limited round trip; it does not prove hosted restore, restoration of photo/PDF artifacts or capacity. Versioned privacy acknowledgement implementation, rights/retention execution, hosted content/signing acceptance, independent security acceptance and source branch protections remain release work.


## 2026-10-29 — membership register account status correction

Prepared current account restrictions as the primary register/detail badge for membership viewers, including delegates without account.view. Historical application decisions and independent membership state remain explicit; account-management links still require account.view. No account or membership mutation, grant expansion or schema change. Synthetic regression coverage includes cancelled/suspended/reactivated accounts, inactive legacy users, membership restrictions and AR/FR/EN rendering. Local checks, PostgreSQL CI, review and hosted acceptance are recorded separately in the PR.
