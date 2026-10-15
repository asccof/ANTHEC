# ADR-019 — multilingual association presentation

Status: prepared for exact-head CI/review, 2026-10-15. Authority: current owner instruction, approved premium palette and POL-01/03/05/06/07.

Replace the minimal CMS layout with a responsive navy/gold/teal presentation, locally served CSS and explicit AR/FR/EN interface copy. No images, fonts, scripts or translation providers are downloaded. The text wordmark uses corrected ANTHEC; approved card/certificate artwork is untouched. Localized CMS title/body, revisions, drafts, publication and restricted translation behavior remain Wagtail-owned; no existing content is overwritten or seeded anew.

Only the actual translated site root gets the landing sections. Child pages retain editorial layout. Membership cards read only effective public membership Price rows; future versions, founder/honorary price overrides, application quotes, people and independent case fees/criteria are excluded. Static rule summaries follow POL-01/03/05/07 and state that association accreditation is not a government licence. No legal registration, qualification or outcome claim is invented.

Owner-testing remains server-side private. Owner sees a prominent trial notice, disabled signup control and administrative navigation; public submission, payments and official issuance/verification remain blocked. All existing privacy guards remain. The presentation is prepared for eventual public use but this is not launch authorization.

Local runtime is disconnected, so no screenshot/visual QA or local pass is claimed. CI must validate metadata, checks/drift, full PostgreSQL tests, recovery and container; exact-head Codex review before private deploy. Owner desktop/mobile/language acceptance follows publication. Actual final editorial content, contact details, legal/privacy texts and independent readiness remain to be supplied/approved; no legal gate or final content acceptance is marked complete.
