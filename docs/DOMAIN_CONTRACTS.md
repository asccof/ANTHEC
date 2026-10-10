# ANTHEEC domain contracts — draft 0.2

Date: 2026-10-10. Consolidates and expands draft 0.1; proposed endpoint error codes and lifecycle details remain design proposals. Task: ENG-004 / issue #3. Status: engineering proposal for review; no business modules are implemented by this document. Executive v1.0 and DDD-001 are the functional basis. Original private source attachments and assessment criteria are not reproduced here.

## 1. Invariants and unresolved policies

Membership applications, activated memberships and accreditations are separate records. A membership tier or verified payment never grants accreditation. Founder/honorary memberships still require an authorized decision; they have no annual expiry, but suspension/cancellation applies. Individual and institution accreditations require a bounded annual interval; course accreditation requires an approved start/end interval matching the approved course. Decisions, financial receipts and issuance history are preserved rather than overwritten or casually deleted.

The implementation must not choose a production policy by reading a convenient code default. These decisions remain with the owner:

| ID | Policy requiring approval | Proposed direction, not an approved rule | Blocks |
|---|---|---|---|
| POL-01 | Tier naming/accreditation-benefit wording | Numbered membership tiers; independent accreditation decision | Public benefit text and award automation |
| POL-02 | Activation origin, calendar boundaries, leap day, early renewal | Explicit local calendar policy in Africa/Casablanca; half-open interval; new renewal term linked to prior term | Validity/renewal calculations |
| POL-03 | Campaign end and renewal price | Versioned tariffs with start/end; immutable quote/payment allocation snapshot | Quoting and charging |
| POL-04 | Decision authority and role combination | Least privilege; financial verification separate action; owner approves delegations | Production grants and approval workflows |
| POL-05 | Public directory/verification fields and serial lookup | Directory opt-in with field selection; opaque-token verification; numeric lookup administrative | Public identity disclosure |
| POL-06 | Collection, retention, erasure/legal holds | Justified minimal fields; explicit retention classes and redaction rules | Real application forms/data |
| POL-07 | Guest/minor eligibility and participant deduplication | No automatic minor enrollment or identity-number collection | Activity eligibility/guest enrollment |
| POL-08 | Reissue, refunds, payment exceptions, annulled decisions | Explicit reason/authority and compensating history | Exceptions and reissue automation |

### Policy traceability and proposal boundaries

The F references below identify findings in INCEPTION_AR.md. Executive and DDD sections identify source requirements or relevant gaps; a reference does not imply that the source approved the proposed solution.

| Policy | Inception findings | Source sections | Source-backed requirement versus new proposal |
|---|---|---|---|
| POL-01 | F02/F03 | Executive §4–5; institutional profile, professional benefits | Independent accreditation is explicit; tier wording is proposed to remove misleading implication |
| POL-02 | F06 | Executive §4/5; DDD §3 | Annual/course durations are explicit; activation boundary, leap-day handling and renewal formula remain proposed |
| POL-03 | F04 | Executive §4 | Current/promotional/reference prices are recorded; campaign end and future renewal charging rule are unspecified |
| POL-04 | F10 | Executive §9; DDD §5 | Separate action permissions are required; actual delegation, role combination and emergency-access model need approval |
| POL-05 | F09/F14 | Executive §4.2/8; DDD §7–8 | Minimal verification and publication consent are required; exact public fields/serial lookup restriction are proposals |
| POL-06 | F14/F15 | Executive §11; DDD §9; institutional profile, application form | Data protection/minimization are required; per-field necessity, retention values, erasure and legal-hold rules remain unspecified |
| POL-07 | F08/F14 | Executive §6; institutional profile §5 | Eligible public/member registration is explicit; account/deduplication/minor enrollment policy is a new proposal to address omitted handling, not a source-authorized restriction |
| POL-08 | F17; relevant finance gap in F04 | Executive §8–9; DDD §4/8 | Reissue/history and manual finance are explicit; refund/exemption/annulment exception rules are new policy proposals because sources do not define them |

These blocks do not stop synthetic development of authorization/transactions. Tests can inject policies explicitly; fixtures must not be presented as institutional approvals.

## 2. Logical entities and constraints

| Entity | Relationships and mandatory constraints |
|---|---|
| PersonProfile | Optional account link, private contact; no mandatory national ID/date of birth/photo inherited from the paper form |
| MembershipApplication | Person + tier + submitted version; applicant owns draft only; reviewed data frozen with decision snapshot |
| MembershipTerm | Person + approved application/administrative grant + decision; renewal links predecessor; bounded annual term or founder/honorary null expiry; no document without valid decision |
| DirectoryConsent | Person/term + allowed fields + time + version + withdrawal; publication independent from term validity |
| Organization | Legal identity separate from a natural person; private responsible contact; public fields separately allowed |
| Course | Organization + approved program reference + date interval; positive interval required |
| AccreditationCase | Exactly one kind-specific subject: person, organization or course; check constraints enforce the discriminator/reference combination |
| AccreditationAward | Approved case + decision + mandatory start/end; status and expiry independent of membership; individual/institution annual policy explicit |
| Payment | Amount decimal + currency MAD + method cash/transfer + reference + status; append corrections, never edit verified amount in place |
| PaymentAllocation | Payment linked to a specific application/case/registration; allocated totals cannot exceed verified funds; no ambiguous `case_ref` string foreign key |
| Receipt | Immutable number, verified payment and issuing actor; adjustments linked to original; uniqueness enforced by database |
| Event | Start/end + capacity + eligibility policy version; registration confirmation owns a seat |
| Registration | Event + participant reference/deduplication key + state; uniqueness rule approved under POL-07; no invitation before confirmation |
| Attendance | Registration unique; verified scanner identity/time; canceled invitation cannot check in |
| Partnership | Organization + proposal + agreement + decision + status; explicit publication authorization independent of status |
| Branch | Region/city + status + publication authorization; local-account scopes deferred to later release |
| Decision | Typed subject reference, action, actor, reason, policy/input version, timestamp; foreign-key integrity or typed link table, not unconstrained generic IDs |
| IssuedDocument | Subject, decision, type, unique serial, template/locale version, generation status, token digest, predecessor/replacement link; private output |
| IdempotencyRecord | Actor/tenant scope + action + key unique; normalized payload hash, resulting resource/status; no secrets in stored request payload |
| OutboxMessage | Created atomically with decision/document; unique event/delivery key; attempt/error timestamps; durable retry lifecycle |
| AuditEvent | Actor, subject, action, request ID, reason, redacted before/after references; application append-only permissions and documented DB administrator boundary |

Use database RESTRICT/PROTECT for deletion of decision/document/payment subjects. Sensitive audit snapshots must minimize identifiers and cannot duplicate raw uploads. Public CMS pages cannot hold application data. Source verification tokens and invite check-in tokens have separate purposes and permissions.

## 3. Transition contracts

All transitions require current object version, authorized actor, prerequisite validation and an audit event in the same transaction. Invalid state is 409, missing required reason/input is 422, insufficient privilege is 403. Record-level unauthorized read returns a generic 404 to avoid resource enumeration. No transition mutates a record through an unrestricted admin form.

### Membership application and term

| From → to | Actor/action | Preconditions | Atomic effects and failure |
|---|---|---|---|
| draft → submitted | Applicant / submit | Required minimal fields and policy acknowledgments; frozen submitted version | Submission event; no term/card; rejected input leaves draft |
| submitted → review | Membership reviewer / claim | Valid delegation, current version | Review event only |
| review → awaiting_info | Reviewer / request information | Reason and requested fields | Request event and optional outbox; no issuing |
| awaiting_info → review | Applicant/resubmission + reviewer | Requested information supplied; new submitted snapshot | Re-review event; earlier evidence retained |
| review → awaiting_payment | Reviewer / request payment | Applicable versioned quote; payment actually required | Private quote/outbox; no acceptance |
| awaiting_payment → review | Finance verification then reviewer | Funds verified and allocated; finance does not approve membership | Financial event plus review eligibility; no card |
| review → approved | Authorized membership approver | Required review complete; payment verified or documented approved exemption; POL-02 policy supplied | Decision + pending-activation term + generation outbox + audit; rollback all on validation/conflict |
| review → rejected | Authorized approver | Reason required | Rejection decision/audit; no term/card; refund policy separate |
| eligible nonterminal → withdrawn | Applicant / withdraw | No final approval; current version | Withdrawal audit; outstanding finance/refunds not silently erased |
| pending_activation → active | Issuance worker | Approved decision remains valid; term policy supplied; artifact generated | Activation + document ready + delivery outbox; failed generation remains pending, no duplicate issuance |
| active ↔ suspended | Authorized membership manager | Reason/delegation; reinstate only if interval remains valid | Decision/audit; verification state immediately follows source |
| active/suspended → cancelled | Authorized membership manager | Reason/delegation | Terminal cancellation; verify invalid immediately; no deletion |
| active/suspended → expired | Time evaluation / system | Approved finite expiry reached | Verification expires immediately, even before periodic state reconciliation |
| expired → new linked term | Authorized renewal flow | POL-02/POL-03; new application/decision/payment if required | Prior term/history retained; no silent alteration of old certificate |

Administrative founder/honorary grants use an explicit application/grant + decision path, not an applicant-selected free membership shortcut. Timing between decision, PDF generation and effective validity requires POL-02; `pending_activation` prevents claiming a ready card before the artifact exists. No worker may decide the business start date.

### Accreditation

| From → to | Actor/action | Preconditions | Effects |
|---|---|---|---|
| draft → submitted → review | Applicant then accreditation reviewer | Type-specific subject and required authorized evidence | Snapshots and audit only |
| review ↔ awaiting_info | Reviewer / applicant | Reason and requested information | Versioned completion/review; private criteria never exposed |
| review → approved/rejected | Accreditation approver | Complete review, authority, reason, input/policy version | Decision only; approval is not yet a ready award |
| approved → pending_issue | Issuance request | Required payment verified/allocated or approved exception; bounded interval validated | Award record + document generation outbox |
| pending_issue → issued | Worker | Approved decision still valid; artifact successful | Ready document/delivery; generation retries are idempotent |
| issued ↔ suspended | Accreditation approver | Reason; reinstatement before expiry only | Decision/audit; immediate verification effect |
| issued/suspended → revoked | Accreditation approver | Reason and current version | Terminal revocation; all linked verify pages invalid immediately |
| issued/suspended → expired | Clock/system | Mandatory valid_until reached | Derived verification first, persisted state reconciliation second |

Rejected or revoked cases cannot jump to issued through an admin edit. A changed award requires a new reviewed decision/reissue process under POL-08. No annual default applies to a course if its approved duration differs.

### Activity registration and attendance

| From → to | Actor/action | Preconditions | Effects |
|---|---|---|---|
| requested → review | Activity reviewer | Eligibility/guest policy; no duplicate participant request | Audit; no invitation |
| review → waitlisted | Activity manager | Eligible but no capacity | Stable queue entry; no seat or invitation |
| review/waitlisted → confirmed | Activity manager | Eligibility/payment conditions fulfilled; capacity checked under event lock | Seat + invitation generation outbox; competing final-seat request conflicts or remains waitlisted |
| review/waitlisted → rejected | Activity manager | Reason | Audit; no invitation |
| requested/review/waitlisted/confirmed → cancelled | Applicant or delegated manager | Cutoff policy and current version | Revoke invitation; release confirmed seat atomically; refunds handled separately |
| confirmed → checked_in | Scoped reception staff / scan | Correct event, valid token, valid confirmed registration | Unique attendance insert; repeat scan returns existing attendance; no second increment |
| confirmed → no_show | Activity manager / after close | Event ended; no attendance | Audit; no automatic certificate |

Attendance correction requires a specific delegated correction action and reason, preserves the original entry and does not create a second check-in. Participation certificates use approved participation criteria, not merely registration or payment.

### Partnerships, branches and documents

| Object | Transitions | Publication contract |
|---|---|---|
| Partnership | proposed → reviewing → active; reviewing → rejected; active ↔ suspended; active/suspended → terminated | Active plus publication authorization; suspension hides current partner listing by proposed default; historical event references follow approved editorial policy |
| Branch | planned → establishing → active; active ↔ suspended; nonclosed → closed | Planned/establishing may be shown clearly as such if authorized; never represented as active. Closed/suspended visibility policy must be explicitly approved |
| Document generation | pending → ready/failed; failed → pending retry | Private file remains unavailable until ready; no second serial on retry |
| Document validity | valid ↔ suspended; valid/suspended → expired/void | Derived from source state, approved interval and explicit invalidation; no stale cache override |
| Reissue | ready predecessor → replacement pending → replacement ready | Link predecessor/reason/template version; whether predecessor is voided requires POL-08; never erase old audit |

## 4. Proposed least-privilege matrix

Owner approves actual delegations and role combinations under POL-04. No account automatically obtains permissions because it has a paid membership. Branch object scopes are reserved, not active in v1.

| Capability | Applicant/member | Content editor | Membership officer | Accreditation officer | Finance officer | Activity officer | Partnership/branch officer | Security admin |
|---|---|---|---|---|---|---|---|---|
| Read own submitted requests/documents | Own only | — | Scoped membership | Scoped accreditation | Financial subset | Scoped event | Scoped partner/branch | No routine business access by default |
| Edit/publish public CMS | — | Delegated CMS subtree | — | — | — | Delegated event content | Delegated partner content | Grants/access management |
| Approve/suspend/cancel membership | — | — | Explicit decision permission | — | — | — | — | Not automatically granted |
| Approve/suspend/revoke accreditation | — | — | — | Explicit decision permission | — | — | — | Not automatically granted |
| Verify payment/issue receipt | — | — | Read eligible status only | Read eligible status only | Explicit finance permission | Read eligible status only | — | Not automatically granted |
| Confirm registration/manage capacity | Request only | — | — | — | — | Scoped decision permission | — | Not automatically granted |
| Check in attendance | — | — | — | — | — | Separate scoped reception permission | — | — |
| Approve partner/branch publication | — | — | — | — | — | — | Explicit publication permission | — |
| Manage users/roles/MFA | Own settings | Own settings | Own settings | Own settings | Own settings | Own settings | Own settings | Explicit security permission |
| Read audit | Own decision summary only | Scoped content | Scoped membership | Scoped accreditation | Scoped finance | Scoped event | Scoped partner/branch | Security events only by default |

Break-glass administrator access is separately granted, reasoned and audited; ordinary security administration is not blanket business authority. Authorization is enforced server-side on every read/write/export/download and worker command. MFA is mandatory for administrative roles before real records. Denial tests must cover ordinary editor attempting finance/accreditation and members requesting another member's file.

## 5. Data dictionary and privacy projections

Retention values below are deliberately `pending POL-06`; no invented legal periods. They must be populated before real data is accepted. No detailed private assessment criteria are defined in this public contract.

| Field group | Collection purpose | Access/projection | Retention |
|---|---|---|---|
| Account email/password hash/locale | Authentication and user-selected interface | Account/security only; never public password hash | Pending POL-06 |
| Person name and needed contact | Administrative application/verified communication | Own + delegated reviewers; directory name only with approved consent | Pending POL-06 |
| CIN/birth date/photo/home address | Not automatically required; needs separate justified purpose | Disabled collection until necessity approved | Pending POL-06 |
| Qualifications/program supporting files | Type-specific accreditation review | Applicant + accreditation reviewers; controlled private download | Pending POL-06 |
| Financial amount/method/reference/allocation | Verify obligations and preserve receipts | Finance + minimal status for decision officers; accreditation fees never public | Pending POL-06 |
| Decision reason/internal review evidence | Accountability and permitted case follow-up | Internal full reason; approved redacted applicant summary | Pending POL-06 |
| Directory consent/allowed fields | Optional public professional listing | Separate opt-in projection; withdrawal removes public fields immediately | Pending POL-06 |
| Document serial/type/effective status/validity | Authenticity verification | Proposed public minimum; holder identity fields await POL-05 | Pending POL-06 |
| Verification/invitation tokens | Unpredictable document/entry lookup | Secret digest in DB; raw token only for controlled rendering/delivery; no logs | Pending POL-06 |
| Attendance event/time | Avoid duplication and establish participation | Participant + scoped event staff; no public attendee list | Pending POL-06 |
| Partner logo/name/branch public details | Institutional publication | Explicit authorization; staff contacts not automatically public | Pending POL-06 |
| Audit/outbox operational metadata | Diagnose authorized actions and delivery retries | Scoped administrative access; payloads minimized/redacted | Pending POL-06 |

Public serializers use an allowlist and never serialize full case models. API errors, exports, logs and translation requests follow the same separation. QR carries an opaque verification URL only, no name/contact/identity number. Verification is read-only and does not authenticate the holder or confer professional authority. Upload acceptance needs MIME/content validation, size limits, malware policy and private storage; those are not implemented by the current CMS PoC.

## 6. Transaction, idempotency and outbox contract

For sensitive commands, require a unique key scoped to authenticated actor + subject + action. Canonicalize validated business payload and hash it, excluding secrets. Store only the digest, resulting resource reference and response metadata. Same key/same digest returns the previous result; same key/different digest returns 409 `idempotency_conflict`. Keys never bypass authorization or expiry; retries re-check the caller's permission before returning private results.

Within one PostgreSQL transaction: acquire subject/event lock; compare object version; validate authority/state/policy/financial prerequisites; create decision and resulting term/award/document intent; insert audit and outbox; persist idempotency result. Uniqueness prevents repeated application approval, serial issuance, delivery intent and attendance even under concurrent requests. Commit precedes processing. A failed commit leaves none of these effects visible. Use consistent lock ordering across event, registration and payment records to avoid preventable deadlocks.

Outbox delivery is at-least-once. A worker claims bounded leases and persists attempt status; expired leases are recoverable. PDF generation uses deterministic document identity and an atomic private-file write; retry never allocates a new serial. Delivery attempts reference the already-created artifact. Transient failure retries with bounded backoff; permanent failure moves to a reviewable failed state. No SMTP exactly-once claim: a timeout after an external server accepts mail may produce a duplicate delivery on retry, but never a duplicate document or decision. Providers remain disabled in the current authorized development environment.

Verification derives validity on each request from source + interval + invalidation. Revocation/cancellation must not wait for an asynchronous worker or an expiry job. Token lookups are rate-limited and logs redact the URL token. Separate check-in endpoints require authenticated scoped staff and an invitation token; a public verification token cannot record attendance.

## 7. Proposed endpoint/error contracts

These routes are design proposals, not live APIs. Administrative routes are session/CSRF/MFA protected, not public JSON CRUD.

| Command/query | Authorization and boundary |
|---|---|
| POST /api/membership-applications | Applicant/approved guest policy; validate minimal fields and abuse controls; returns application only |
| POST /admin/membership-applications/{id}/approve | Explicit membership decision + version + idempotency; ID refers to existing application, not an uncreated membership |
| POST /admin/membership-terms/{id}/suspend or cancel | Explicit action permission and reason; immediate verify effect |
| POST /admin/payments/{id}/verify | Finance only; no membership/accreditation acceptance side effect |
| POST /admin/accreditation-cases/{id}/decide | Accreditation decision permission; private policy version and bounded interval validation |
| POST /events/{id}/registrations | Eligibility policy, participant deduplication; no invitation |
| POST /admin/registrations/{id}/confirm | Scoped event permission; atomic seat/decision/invitation intent |
| POST /admin/attendance/check-in | Scoped reception staff + event + invitation token; returns original attendance on repeat |
| GET /verify/{opaque_token} | Public read-only minimum projection; no caller-selectable expanded fields |
| GET /member/documents/{id}/download | Owner or delegated document permission; private file, short lifetime/no public media URL |
| POST /admin/partnerships/{id}/publish | Explicit publication consent + active status/policy; audit |

Error envelope: `{code, message, request_id, field_errors?}`. 401 unauthenticated API; 403 forbidden action; 404 inaccessible/unknown record or token; 409 invalid state/version/idempotency/capacity conflict; 422 validation failure; 429 rate limited. Responses must not reveal internal accreditation criteria, fees, other applicants, provider credentials or stack traces. Browser forms may use redirects for authentication/permission denial; they still require negative mutation tests.

## 8. Required test scenarios for implementation

| Reference | Scenario and assertion |
|---|---|
| AC-03/05; T01/02 | Ordinary/founder/honorary requests or verified payment alone produce no ready card; explicit approved decision required |
| AC-04 | Policy-injected calendar tests for leap day, DST/timezone boundary, delayed generation and early renewal; no silent default |
| AC-06; T03 | Consent withdrawal hides directory fields but leaves otherwise valid card valid |
| AC-07/13; T05/08 | Public endpoints/errors/exports expose no private criteria/fees; content editor cannot decide accreditation or verify payment |
| AC-08; T09 | Revocation immediately changes verify response even if outbox worker is down |
| T10; AC-14 | Crash before commit creates nothing; crash after commit preserves outbox; retry creates one decision/document/serial; audit remains |
| AC-09; T06 | Registration does not issue invitation before confirmation; final-seat concurrent confirmations allow only one seat |
| AC-10; T07 | Concurrent scans yield one attendance record; invalid/cancelled/wrong-event tokens fail without a write |
| AC-11; T11 | Publication authorization and administrative state jointly control partner/branch visibility; no automatic authority from a proposal |
| Document reissue | Old/new references remain linked; invalidation follows approved POL-08 and survives retry |
| Record privacy | Members cannot read/download another member's case/file; workers/exports obey the same scope |
| Outbox delivery | Retry does not reissue a card; uncertain mail delivery may duplicate mail but never document identity |

Full original criteria remain planned until these scenarios and all other source requirements are implemented and evidenced on the reviewed SHA.
