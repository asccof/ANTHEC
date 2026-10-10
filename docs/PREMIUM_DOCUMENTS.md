# Approved premium documents — bounded integration

## Owner visual approval

On 2026-10-10 the owner explicitly approved the reference-inspired v4 proofs: accredited member gold card (front/back), president executive card (front/back), professional accreditation certificate. Public acronym is **ANTHEC**; repository/internal identifiers remain ANTHEEC. The already-approved emblem stays unchanged. This supersedes unapproved earlier design alternatives; POL-01–08 are unchanged.

Cards: CR80 85.60 × 53.98 mm, double-sided; PVC 0.76 mm is manufacturing guidance. Certificates: A4 landscape 297 × 210 mm. Navy/gold/ivory with restrained emerald/turquoise. Localized AR/FR/EN; original Arabic/French institutional wording. No unverified English legal name. No invented seal/signature/government authority.

The approved certificate proof background is only 127.43 effective DPI. **Visual approval is not print-readiness acceptance.** Reconstruct its decoration as vector or genuinely high-resolution artwork before production print release. Card artwork is about 468.54 DPI. Fonts are SIL OFL; text/QR should remain vector. Physical printing, scanner/duplex alignment, supplier profile and optional bleed must be validated; no unsupported CMYK/PDF/X claim.

Private original reference sheets/association attachments are not committed. Synthetic-only test assets may be committed for bounded non-production implementation.

## Package A — protected portraits and snapshots

`Portrait` retains each normalized review record with a random UUID, consent audit, uploader, explicit pending/approved/rejected state and administrative decision evidence. Only JPEG/PNG single-frame content up to 3 MiB and 16 million pixels is accepted. Integrity is verified, EXIF orientation corrected, centered 4:5 crop previewed, and metadata stripped into a 600 × 750 JPEG. No facial recognition, matching or automatic identity decision. Original input is discarded.

Normalized JPEGs are Fernet-encrypted in the existing protected database using the existing data-key service. There is no media file or public/predictable media URL. Random UUID retrieval still enforces ownership/authorized guardian or live administrative MFA/delegation. Images and private pages are no-store. Review commands additionally require recent password/factor verification and reasoned audit. Upload does not grant membership, accreditation, office or admin rights.

Issuance binds the latest approved portrait to applicable card records. The FK is PROTECT and the snapshot is not rebound when a new photo is uploaded or approved. Existing issued cards with no portrait stay unbound; formal audited reissuance through existing commands is required to adopt one. A photo-capable final PDF must fail closed as pending-photo when this snapshot is absent. The legacy HTML service remains backward compatible in this package; PDF pending-photo enforcement belongs to package B.

Routes: member/guardian `/members/portrait/`, MFA-protected `/operations/portraits/`, authorized `/private-portraits/<uuid>/`. Every state mutation is POST/CSRF with scoped choices and existing replay/transaction boundaries. Audit never includes image data or original filenames. Existing legal readiness (retention, rights handling, notices, hosting/CNDP review) remains a prerequisite to real-data deployment; no statutory conclusion or retention period is invented.

## Subsequent packages and gates

B: implement the approved shared design system and supported card/certificate renderers; protected PDF previews/downloads, immutable language-specific artifacts, issuance outbox integration, print/QR/font/language regressions. Existing categories only: general, affiliate/associate, advanced, accredited, founder, honorary; institutional president/vice_president/founder. Founder/permanent and office validity follow existing records. Participation has no approved issuance command/eligibility contract; do not infer it from a template.

C/acceptance: focused PostgreSQL and security/end-to-end checks, CI and exact-head mandatory Codex review, findings resolved, merge in dependency order, post-merge verification. No production deployment, paid services, real people, external notifications or later-phase activation.

Status: package A prepared; local tests/CI/review/acceptance are recorded separately in STATUS.md and PR evidence. Package B is pending. This document does not claim implementation acceptance.
