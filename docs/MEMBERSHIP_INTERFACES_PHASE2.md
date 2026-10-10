# Phase 2 membership and administration interfaces

Owner authorization: 2026-10-10, approval of the Phase 2 mandate. Baseline live main 6196e32704321b21e8deb4717c44673fd3b5242e (PR #16). Issue #17 tracks delivery, alongside broader #6. POL-01–08 and Phase 1 remain authoritative and unchanged.

## Packages and gap map

| Package | Existing core | Missing interface / bounded change |
|---|---|---|
| A | Person account uniqueness; versioned fixed quotes; application service; CSRF/authentication/audit | Signup/signin/POST logout/password change; own profile, notice and optional directory consent; own initial application; account-row locking/idempotency and duplicate submission guards |
| B | MFA primary/delegation; approval; cash/transfer verification; exemptions/refunds | Protected application register/detail, reasoned rejection, financial decisions and history; deliberate linkage of a legacy Person to an account |
| C | Early/late renewal; separate gold card/certificate; institutional documents; protected download | Own renewal selection and documents/receipts/status history; integrate institutional records without reimplementing grant/state services; complete synthetic journey |

Each package requires metadata checks, Django/migration/dependency checks, PostgreSQL CI and exact-head Codex review before merge. Acceptance evidence belongs to each PR; prepared code is not accepted code. When external review availability blocks acceptance, dependent packages may be prepared on stacked draft branches. None may merge until its dependency is accepted, the PR is retargeted to live main, and PostgreSQL CI plus exact-head review are revalidated.

## Technical boundaries

Account creation grants no Person eligibility, membership, accreditation or administration. Signup uses the existing Django password validators; signin uses generic authentication errors and a hashed fixed-window IP throttle shared with signup/password changes. Logout is POST-only. Sensitive password fields are excluded from error reports. No password recovery/email verification delivery is invented; offline administrative recovery remains a separate readiness concern.

A self-service profile operates solely on Person.user=request.user. Account-row locks and the existing unique user relation prevent duplicate profiles under concurrency. Existing noticed profiles are reused; managed minor/guardian identity cannot be overwritten. Name/email alone never authorizes linking a preexisting unlinked record. The interface asks previously recorded applicants to seek administrative linking before creating a new profile. Cross-account real-world identity deduplication is not claimed.

Verification notice acknowledgment is explicit, separate from optional directory consent. No directory is published in this phase. Profile correction preserves issued holder-name snapshots; document correction/reissue remains an administrative operation. Member audit events retain action/record/notice version/consent, not profile contact or raw passwords.

Initial applications use the fixed quote service and one pending application per account-linked person. An existing membership uses renewal instead; tier upgrades or parallel initial memberships are not invented. Founder/honorary requests remain subject to administrative decision. Submission and payment never approve membership or create cards. Self-service command keys are scoped to actor/action with payload-digest replay protection and account locks; administrative commands keep their existing Authority/MFA boundary.

Synthetic data only. No production deployment, real persons, external notifications, paid services, independent accreditation casework, events, partnerships or production PDFs. Protected/legal readiness gates remain open.

## Package B interface behavior

`/operations/membership/` lists the latest 100 applications; detail pages expose review/approve/reject, cash/transfer proof verification, reasoned exemption/refund, membership state and document reissue using existing services. Reads require live primary/delegation and MFA; sensitive writes also require recent password/factor. CSRF and origin-scoped payment/document choices reject cross-application manipulation. Rejection only changes submitted applications and records the reason; it never erases payments or automatically refunds them. State decisions retain linked accreditation and future-term propagation from the core.

`/operations/membership/identities/` deliberately links an unlinked adult Person to an active account with no existing Person after recorded administrative identity verification. It never transfers an already linked record, merges accounts, changes minor/guardian fields or confers privileges. Operators must link legacy records before self-service profile creation. Existing duplicate real-world identities require separate verified remediation, not a name/email merge heuristic.

All payment proofs, exemption/refund/internal decision reasons and administrative history remain behind the director boundary. Member records show only their own fixed amounts/states/receipts; public verification keeps its original allowlist. Refund decision recording does not execute a bank transfer.

External acceptance blocker observed: Codex GitHub review requests for package A were rejected because review usage was exhausted. No credit purchase/paid service is authorized. Package A PostgreSQL run 38064423647 passed 101 application/CMS tests and six metadata tests; it remains unmerged. Packages B/C are stacked drafts pending that mandatory review gate.
