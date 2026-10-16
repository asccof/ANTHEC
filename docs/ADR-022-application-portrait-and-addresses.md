# ADR-022 — Portrait and private addresses at membership intake

Date: 2026-10-16
Status: prepared; final CI, external review and owner UAT pending

## Owner decision

The owner approved uploading the portrait during a new membership application, before first card issuance. Professional applicants provide correspondence and professional addresses, with an explicit same-address option. Beneficiaries provide residential address only, used for correspondence. The address category is explicitly selected; it is independent of membership tier and does not confer professional standing or administrative rights.

## Implementation boundaries

New self-service requests require JPEG/PNG portrait and explicit consent. Existing normalization, encrypted storage, private authenticated image route, review and audit apply; originals are discarded. Submission atomically stores the pending portrait and application, with account serialization and idempotency. Approval of new intake waits for the linked portrait to be approved. A replacement uploaded from the existing Portrait page updates pending new-intake requests only; rejected or pending replacements block approval. First card binds the exact approved application portrait. Later uploads never rewrite approved requests or issued documents; formal reissuance remains necessary. Person locks precede Application locks for approval and replacement.

Addresses are bounded to 1000 characters each, validated at browser and command boundaries, shown only on private application pages, escaped by templates and excluded from audit details, public verification, directories and PDF artwork. Opposite-category fields are rejected server-side, not merely hidden. No diagnosis, clinical history or real-person data is needed for synthetic UAT.

Additive migration 0011 leaves legacy requests at intake_version 0 with blank addresses and no fabricated portrait link. Existing administrative intake and renewal flows remain compatible; this increment changes new self-service applications only. Existing cards, certificate artwork, signing rules and POL-01–08 remain unchanged. The host remains private, public workflows disabled, no resources or plans changed, no Tighri or MHIOS changes.

## Verification

Regression coverage includes required multipart form fields in AR/FR/EN, invalid-image rollback, idempotent upload/application replay, address category validation, private access, pending/rejected portrait approval guard, replacement before approval, paired accredited issuance and immutable issued snapshots. PostgreSQL CI and exact-head external review are required before merge. Owner local UAT and hosted deployment are distinct pending milestones. Local response latency remains explicitly deferred.
