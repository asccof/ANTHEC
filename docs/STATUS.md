# Execution ledger

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
