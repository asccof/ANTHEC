# ADR 027: Institutional card administration presentation

Date: 2026-10-18
Status: Prepared; final review, PostgreSQL CI and owner visual acceptance pending.

After accepting the membership administration presentation, the owner authorized continuing the interface work. Institutional cards still used a separate legacy layout.

Reuse the private member palette and typography, with a dedicated institutional stylesheet and scoped markup. Group grants, latest-100 role cards, recorded role state and term dates, issued cards, state/reissue commands and decision history. Explicitly label the recorded role state separately from each document's effective status; do not infer card validity from the stored role state. Keep localized download/preview captions, bound errors, CSRF tokens, idempotency keys, existing routes and service validation. No schema, artwork, financial policy, authority or hosted deployment changes.

Local tests cover recorded-active/expired-card separation, permanent founders, escaped identities, localized actions and bound errors. Final validation evidence belongs in the PR. Automated browser visual acceptance is not claimed.
