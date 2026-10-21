# ADR033 — Remaining public and administrative presentation

Date: 2026-10-21. Scope authorized by the owner's request to complete remaining work, with the private-trial/no-spend/no-hosted-deployment boundaries preserved.

## Change

Public partners, partnership request, document verification and browser verification results use one responsive navy/gold/teal public shell with local fonts/logo, locale navigation, member/home links and the existing trial-aware verification control. No fictional partners, ratings, endorsements or agreements are invented. Only the existing approved/active/visible public partner projection is shown; private request contact/message/reasons are never added to it.

The proposal explains review, lack of automatic acceptance/accreditation and private contact handling. Disabled hosted-trial submission remains a disabled fieldset, not a POST form. Administrative partnership register/review/edit pages use state badges, separate request/partner sections, explicit decision captions and preserved scoped forms/history. Localized partner names display in the selected locale. Independent accreditation register/case pages reuse the private design and existing permission controls, remove duplicated final assessment display and keep private criteria/fees/history private. Child page-title/heading blocks improve operational headings while defaults preserve other member pages.

The browser-only verification failure path now returns the existing form with localized generic error at HTTP404, or HTTP429 for throttling. It does not reflect serial, token or code. JSON clients retain the existing payload/status contract. Success field allowlist, lookup behavior, CSRF, QR-fragment-to-POST flow, same-origin form/referrer behavior needed by HTTPS CSRF fallback, no-referrer result pages and no-store protections, rate limits and trial middleware are preserved. No new validity/issuance policy or public name lookup.

## Evidence and limits

Existing partnership, independent accreditation, institutional/invitation verification and content checks plus new HTTP privacy/CSRF/throttle/JSON-compatibility regressions are required; PostgreSQL/container/recovery CI and exact-head review are distinct PR evidence. No automated browser/mobile screenshot acceptance is claimed. Owner visual UAT remains pending.

No schema migration, Gemini provider/config change, private upload, external email/payment, branch governance, hosting deployment, paid resource, DNS, Tighri or MHIOS modification. Broad original requirements and release gates are not silently marked complete by a presentation increment; see CURRENT_COMPLETION_AR.md.
