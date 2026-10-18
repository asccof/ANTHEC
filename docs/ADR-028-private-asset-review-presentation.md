# ADR 028: Private portrait and signing asset review presentation

Date: 2026-10-18
Status: Prepared; final tests, PostgreSQL CI, exact-head review and owner visual acceptance pending.

The owner approved continuing the administration interface with portrait and signature/stamp review. Use scoped responsive galleries with private preview URLs, clear file references, states and upload/review dates. Label review options with holder name or localized asset kind plus immutable reference. Explain oldest-100 pending portrait and latest-100 signing asset windows; only pending assets within the existing visible batch remain reviewable. Historical approval must not imply the asset is the latest selected for new issuance.

Keep upload and review forms and bound errors visible even for empty queues. Preserve CSRF/idempotency, recent MFA, primary-only signing assets, authorized portrait review, encrypted image storage, audit, immutable issued artwork and formal reissuance. Lazy loading reduces eager preview fetches; this is not a diagnosis or resolution of the deferred latency issue. No schema, policy, hosting or release changes.

Final validation evidence belongs in the PR. Owner visual acceptance is separate; no automated browser screenshots are claimed.
