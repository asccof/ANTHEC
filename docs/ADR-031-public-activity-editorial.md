# ADR 031: Linked public activity presentation and editorial administration

Date: 2026-10-19
Status: Prepared locally; final PostgreSQL/container/recovery CI, exact-head review and owner visual acceptance pending.

## Owner authorization

After accepting PR48 login/delegation behavior locally, the owner explicitly deferred latency investigation and requested the public activity page and its linked administrative authoring: descriptions, images, useful/video links and improved content/layout. This increment does not authorize hosted deployment or release, paid resources or changes to Tighri.

## Public content and presentation

Activity retains its existing title/dates/capacity/minor-consent fields and gains bounded validated presentation JSON plus a public editorial visibility flag. Local public `/activities/` lists visible upcoming/ongoing activities, a separate past archive and pagination. `/activities/<id>/about/` shows manually supplied AR/FR/EN introduction, description, programme, audience, speakers, venue, activity category/format and up to four named HTTPS resource/video links. Missing translations fall back to source text; no translation service or automatic remote fetch/embed is used. Text is escaped, not interpreted as arbitrary HTML. Video links open explicitly in a new protected tab. Existing authenticated participation routes remain separate.

Navy/gold/teal layouts share the established site assets and navigation, with responsive cards, a detail/sidebar layout, gallery and explicit participation links. Activity administration groups editorial fields by language, links, media, conditions and visibility; bound errors remain visible. Public pages show the synthetic-data notice. Automated HTTP/template checks are not desktop/mobile visual acceptance.

## Media and exposure

ActivityImage is a distinct public-editorial asset; private portraits, signatures and issued document snapshots are never reused. Upload accepts bounded single-frame PNG/JPEG, checks dimensions/pixels, strips metadata, preserves aspect ratio and normalizes to a maximum 1600x1200 JPEG. At most six active images per activity, with the first active image as cover. Bytes stay in PostgreSQL, requiring no public filesystem route or new storage service. Lists defer binary payloads. Withdrawal is recorded and deactivates retrieval while preserving audit/history. Public image requests recheck parent visibility and active image state; administrative draft previews require activity.view. Responses are no-store so hiding/withdrawal does not leave an application cache serving old media.

Migration0013 defaults all existing activity editorial pages to hidden; no old record is automatically exposed. Existing registrations, admission/attendance commands, capacity and frozen participant conditions remain unchanged. Visibility governs the new public editorial page/media; existing authenticated participation/history remain the established member workflow. The hosted owner-testing middleware remains primary-only and blocks anonymous access even when an editorial flag is enabled. Registration/payment/issuance/release gates are unchanged.

## Delegation and writes

Four explicit capabilities extend the activity group: publish, hide, image_upload and image_remove, each requiring activity.view. Existing grants gain no new capability automatically. Publication can be performed independently from editing; upload/removal remain separate. Editing visible activity content/configuration or adding a live image requires the relevant edit/upload capability plus activity.publish, checked cumulatively under the Authority lock. Thus an editor cannot silently publish through an already-visible record. Image withdrawal has its own explicit scope and does not grant whole-activity hiding. Published content saves take effect immediately; a delegate lacking publication must work on a hidden activity.

Create/update with an optional first image is atomic across existing activity commands and media upload; a bad/unauthorized image rolls back the new activity or changes. All commands retain session epoch, active account, exact scope, primary login MFA, CSRF, idempotency and audit. Primary grant management remains unchanged.

## Validation and limits

New HTTP/service regressions exercise anonymous visibility/archive/locales, source fallback, escaped descriptions, unsafe links, publication prerequisites, normalized image retrieval/withdrawal/origin scope and gallery limits, atomic failed creation, independent publisher/uploader rights, published-edit cumulative scopes and unchanged owner-testing/CSRF gates. Existing activity, membership and scoped-delegation suites remain required. Final CI and external review evidence belongs in the PR; owner visual and real-content acceptance remain pending. No uploaded file, private asset or real person data is committed.
