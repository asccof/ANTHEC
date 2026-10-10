# ANTHEEC domain contracts — draft 0.1

Status: proposed engineering contracts, not approved business policy or implemented endpoints.
Sources: Executive Specification v1 §§4–9/11 and DDD-001 §§3–9; reconciles inception findings F05–F10/F14/F16/F17.
Independent of MHIOS. Development uses synthetic fixtures only. This document contains no accreditation evaluation criteria or fees.

## Aggregate and data boundaries

| Aggregate | Responsibility | Required invariant |
|---|---|---|
| MembershipApplication | Requested tier and review | Submitted application is not active membership |
| Membership | Approved right with activation and validity | Requires explicit approval decision, including founder/honorary |
| Payment | Reported/verified funds | Payment alone grants neither membership nor accreditation |
| AccreditationCase | Individual, institution or course review | Subject is an explicit typed foreign key, not ambiguous applicant_id |
| Accreditation | Approved professional/training right | Separate decision; mandatory valid_from and valid_until |
| Registration | Participation request and confirmation | No invitation before confirmed state |
| Partnership | Agreement and publication consent | Active status and publication permission both required |
| Document | Issuance identity and rendering | Unique serial; origin approval required; retries preserve identity |
| Decision/AuditEvent | Recorded authorization and history | Append through service; no ordinary edit/delete |
| OutboxMessage | Durable pending side effect | Created in the same transaction as the originating decision |

Use database constraints for exactly one accreditation subject; valid_until > valid_from; unique attendance(registration); unique logical issuance(origin,type,version); unique idempotency(actor,action,key). These are design targets requiring PostgreSQL tests.

Founder/honorary membership has no expiry but remains subject to approval, suspension and cancellation. Other membership lasts one year; exact boundary/activation/leap-day and renewal policy await owner approval. Individual/institution accreditation lasts one year; course accreditation lasts the approved course duration. No perpetual accreditation.

## State transitions

All transitions require authenticated action permission, object scope, server-side prerequisite checks and audit. A UI button is not authorization.

| Subject | Transition | Prerequisites and atomic effect |
|---|---|---|
| Membership application | draft → submitted | Valid required fields; tier/pricing snapshot; submit event |
| Application | submitted → review | Assigned membership reviewer |
| Application | review → awaiting_info / awaiting_payment | Explicit reason and requested action |
| Application | awaiting_info/payment → review | Required response/payment verification recorded |
| Application | review → approved | Approver permission; verified applicable funds or authorized exemption; approved policy version; decision + membership + pending document + outbox |
| Application | review → rejected | Explicit reason and rejection decision; no membership/document |
| Membership | active ↔ suspended | Authorized action, reason and decision |
| Membership | active/suspended → cancelled | Authorized cancellation, retained history; no silent resurrection |
| Membership | active → expired | Derived from approved validity boundary; cannot be hidden by cache |
| Accreditation case | submitted → review → approved/rejected | Authorized assessment; approved subject and bounded validity |
| Accreditation | active ↔ suspended; active/suspended → revoked | Authorized reason and decision; public verification reflects current origin immediately |
| Registration | requested → review → confirmed/waitlisted/rejected | Scoped events officer; capacity lock; invitation only on confirmation |
| Registration | confirmed → cancelled | Invalidate invitation and release capacity atomically; cancelled attendee cannot check in |
| Attendance | absent → checked_in | Confirmed registration, valid invitation, authorized scanner; unique insert |
| Partnership | proposed → reviewing → active ↔ suspended → terminated | Authorized agreement review; separate publish_allowed flag |
| Branch | planned → establishing → active ↔ suspended → closed | Explicit delegated authority; public display policy awaits approval |

Restoring revoked/cancelled rights is a new governed decision/record if later authorized, not a CRUD reversal. Rejected application resubmission and early renewal require policy definitions before implementation.

## Permission proposal

Role assignment and segregation of duties await owner approval. Technical administrator does not receive business approval solely by being able to manage accounts; emergency superuser access is auditable and restricted.

| Action | Membership officer | Accreditation officer | Finance officer | Content editor | Events officer | Partnership officer | Member |
|---|---|---|---|---|---|---|---|
| Review membership | Scoped | No | Payment reference only | No | No | No | Own status |
| Approve/cancel membership | Explicit delegation | No | No | No | No | No | No |
| Decide/revoke accreditation | No | Explicit delegation | No | No | No | No | No |
| Verify funds/receipt | Read reference | Read reference | Scoped | No | No | No | Own record |
| Edit/publish institutional content | No | No | No | Scoped | Activity content only if delegated | Partner content only if delegated | No |
| Confirm/check in activity | No | No | No | No | Scoped | No | Own registration |
| Decide partnership/publication | No | No | No | No | No | Scoped | Own request if applicant |
| Download personal documents | Scoped need | Scoped need | Receipt only | No | Invitation only | Agreement only | Own documents |

Reject cross-record and cross-branch access even with action permission. Finance verification and business approval are distinct actions. No editor receives sensitive business permissions by CMS access.

## Service and failure contracts

Proposed command endpoints (not implemented): application submit; membership-application/{id}/approve; membership/{id}/suspend/cancel/visibility; accreditation-case/{id}/decide; accreditation/{id}/suspend/revoke; registration/{id}/confirm/cancel; attendance/check-in; partnership/{id}/decide/publish-permission.

Sensitive commands accept an idempotency key and a validated payload. Canonicalize semantic input and store a hash. Same actor/action/key and same payload returns the original outcome. Different payload returns conflict without mutation. Lock the subject row; check its current state; create decision, audit event, result and outbox inside one transaction. Rollback leaves no partial approval.

Outbox workers retry rendering/delivery with bounded backoff and inspect unique issuance keys. Rendering failure keeps the document pending; delivery failure never creates a new serial or decision. Worker crash after sending may duplicate delivery unless the adapter supports deduplication; exactly-once delivery is not claimed. Synthetic memory-only adapters until separately authorized.

Use 400 validation, 401 unauthenticated, 403 denied action, 404 inaccessible/unknown object, 409 invalid transition or idempotency conflict, and 503 unavailable adapter. Responses/logs never contain private criteria, fees, identity numbers, raw verification tokens or attachments.

## Public verification and data minimization

Opaque high-entropy verification token; store a hash, not a serial-based public search index. Final public fields await approval. Development response defaults to document type, current validity status and no personal fields; this is a safe test proposal, not a production privacy decision. Derive suspension/revocation/expiry from the origin on every verification; do not cache an active result across revocation. QR encodes only a verification URL.

Private data dictionary proposal: legal name (identity/issuance), contact address (delivery), locale (UI), tier snapshot (membership processing), financial reference and verification (accounting), agreement reference (partnership governance). Record justification, access scope, retention period and deletion basis for each before collecting real data. CIN, birth date, photo and home address are excluded until a necessity decision exists. Directory visibility/allowed fields/consent are separate from validity.

Attachments remain private; size/type validation, malware scanning strategy, download permission checks and retention must be defined before enabling uploads. No clinical records. Guest accounts, participant deduplication and minor eligibility remain unresolved.

## Required evidence before implementation acceptance

- Concurrent approvals and last-seat confirmations on PostgreSQL create one valid outcome.
- Same-key replay succeeds; changed payload conflicts; unauthorized actor creates no decision/outbox.
- No card before approval; founder/honorary requires approval; hiding directory leaves card validity unchanged.
- Editor cannot verify funds or decide/revoke accreditation; one member cannot fetch another member's records.
- Revocation is visible immediately; wrong/expired token discloses no identity.
- Render/send retry preserves serial and approval; forced rollback/crash exercises durable outbox.
- Duplicate attendance creates one record; cancelled invitation is unusable.
- Public serializers, errors, exports and navigation contain no private accreditation criteria/fees.
- Review required: owner policy decisions and privacy fields; technical self-review; CI on final SHA; external Codex review.

Issue #3 tracks these contracts. CMS completion/MFA precedes real business-user workflows. These contracts do not authorize production, paid services, integrations or real-person data.
