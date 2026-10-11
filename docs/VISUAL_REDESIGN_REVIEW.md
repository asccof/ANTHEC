# Focused credential redesign - owner review draft

Source: asccof/ANTHEC main `6b6ab8d43d68abcd079caed2a2edf684dd4925b8`, re-fetched on 2026-10-11. Branch: eng/credential-visual-refinement. The owner authorized focused redesign, proof collection and relevant engineering review. No final visual approval, merge, deployment or participation issuance is authorized.

## Change log

- President PNG artwork, original ANTHEC logo and licensed font outlines are preserved byte-for-byte. Only content/localization, front-reference removal, reading positions and necessary print contrast treatments change on the President card.
- Seven original category compositions use vector borders, engraved acanthus, fine guilloche, controlled color and quiet paper texture. General: ivory/navy bowed corners; Affiliate: turquoise side arcs; Advanced: midnight octagonal frame; Accredited: champagne/navy ceremonial double frame; Vice-President: ivory/navy institutional cornices; Founder: emerald with paired side foliage; Honorary: ivory/gold diplomatic double frame. These are bespoke deterministic vector compositions, not eight recolorings of one background. They are programmatically drawn artwork, not recovered details from the owner reference or commissioned physical engraving.
- Fronts contain portrait, category, full holder name and recorded validity. Full UUID appears only on the reverse. No unapproved short identifier is invented. General display labels are now عضو / Membre / Member; internal general key, price, permissions and rules are unchanged.
- QR quiet zones have white mounts on all backgrounds. All issued-document QR payloads still use the configured origin and existing fragment workflow; no public search, fields or endpoint changes.
- Certificates use original vector navy/gold ornament and a separate emerald participation proof. Recorded accreditation subtype (professional/individual/institution/course), holder/subject, issue date, validity and UUID are printed. Mixed dates are separate LTR text boxes. No seal, signature image, statutory licence or additional accreditation right is invented.
- Name fitting scales each box from its own original size; long activity/organizer fields cannot inherit holder-name font sizes. Text is escaped; network/file/data retrieval remains closed.
- Existing encrypted PDF snapshots, protected portrait snapshots, MFA/authorization/lifecycle locks, outbox, audit history and policies POL-01 to POL-08 are unchanged. No migration, model, issuance service, route or security configuration change.

## Content and data mapping

| Printed field | Existing data / limitation |
| --- | --- |
| Card category | Membership application tier or InstitutionalRole.role |
| Holder | Document.subject_name issuance snapshot |
| Portrait | Document.portrait approved protected snapshot |
| Effective dates | public_document origin starts_on / ends_on, not a new annual office assumption |
| Founder/honorary permanence | Existing nullable end rules; no new exemption |
| Complete verification reference | Document.serial on reverse / certificate |
| Verification code / QR | Existing encrypted credentials; public origin configured by application |
| Certificate scope | Accreditation.kind plus recorded subject; no detailed profession/specialism field exists |
| Issue date | Document.issued_at; legacy NULL remains unknown |
| Signature | Blank authorized-signature area; no approved signature asset / signatory field exists |
| Decision number | No approved printable public decision-number field; none invented |
| Association names | Existing Arabic/French wording retained; English is a proposed working translation requiring owner content acceptance |

The proposed English translation is "National Association for Psychological and Family Therapy and Coaching". It is not represented as a registered English legal name.

The existing exclusive end-date semantics are unchanged. Synthetic office examples deliberately use a recorded multi-year term, while annual membership/accreditation uses its own recorded term. No real governance/owner records were read or altered for specimen generation.

## Participation: proof only, issuance remains absent

The pure ParticipationProof value object contains explicit synthetic participant, training, organizer, activity dates and optional duration. It has no database writes or issuance command, and no route exposes it. Normal document rendering still rejects participation_certificate. The printed reference is NOT ISSUED; its labeled non-operational QR encodes that design-proof statement, never an invitation token or a verification URL. No fake participation number or authorized signature is supplied.

Before activation the owner must approve: eligible attendance/completion criterion, issuing actor/authority, whether training completion differs from attendance, source of organizer and duration, replacement/revocation/validity policy and signatory evidence. Activity title/dates and attendance infrastructure already exist; organizer/duration and a participation-document issuance relationship/contract do not. This increment proposes no new business policy or schema.

## Evidence and acceptance boundary

Review collection: 24 two-page card PDFs, six existing-certificate PDFs, three participation-proof PDFs = 33 PDFs / 57 PNG pages, AR/FR/EN. Individual PDFs have CR80 85.60 x 53.98 mm or A4 landscape 297 x 210 mm trim. Enlarged collection pages are for review; print individual proofs at 100 percent. Synthetic names/portraits and example.invalid targets only.

Targeted PDF suite: 19 passing tests; six metadata tests, standalone baseline validator, Django checks and migration drift checks pass locally. Full current-head regression, PostgreSQL CI and Codex review are tracked separately in the draft PR and review report. Local SQLite is not evidence of PostgreSQL compatibility.

Owner must inspect every face/language. Automated dimension/font/QR/page-bound checks do not establish visual approval. Digital QR decoding does not certify a physical card scanner. Physical duplex alignment, rounded-corner cutter clearance, CMYK/supplier profile, metallic foil and PDF/X remain outside current validation. All output is RGB and visibly marked specimen; production remains blocked.
