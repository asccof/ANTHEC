# ADR-023 — Homepage mission, audience pathways and public association structure

Date: 2026-10-17
Status: prepared; exact-head CI/review and owner visual acceptance pending

## Owner request and scope

After successful local synthetic membership/document/payment UAT, the owner requested homepage content and visual refinement before the remaining page families: association mission/goals/services for beneficiaries and professionals, membership/accreditation/activities/partners, navy/gold/turquoise identity, AR/FR/EN and mobile, and the president, vice-president and founding council names. This bounded increment covers the homepage and shared public header only. Member/operations interface refinement and unresolved local latency remain separate.

## Decisions

Use the existing approved logo unchanged and locally bundled OFL Arabic UI fonts. Add mission/goals and two audience pathways, describing areas of work without claiming live appointment services, clinical outcomes, government licensing, external partnerships or an official launch. Retain membership price version lookup, existing accreditation notices, private assessment/fee boundaries and trial gates. Keep the existing published editorial body available in a disclosure rather than destroying CMS content. A local synthetic preview notice remains visible; owner-testing retains its disabled signup and anonymous gate.

Public structure names come from explicit leadership blocks in the translated homepage CMS body, using role plus plain-text name. The existing Wagtail publication and translation workflow applies. No account, Person, Authority, InstitutionalRole, contact data or uploaded portrait is queried to populate public names. Missing roles show a neutral pending-publication message. No real name is seeded or committed; the owner must supply the approved publication list and localized spellings. Adding this block changes the StreamField schema via content migration 0002 without rewriting existing body values.

## Evidence and limits

Content tests cover all three locales, services/structure anchors and copy, explicit published names, escaping and no private institutional identity auto-disclosure. Existing current-price, private-data, child-page/editorial and hosted owner-gate regressions remain required. System/migration/metadata checks and PostgreSQL CI precede acceptance. Browser automation is attempted separately; failed browser installation is not visual evidence. Desktop/mobile owner inspection remains pending. No hosting/resource/cost, Tighri, MHIOS, card/certificate artwork or public release changes.
