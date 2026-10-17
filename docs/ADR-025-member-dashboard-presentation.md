# ADR-025 — Private member dashboard presentation

Date: 2026-10-17
Status: prepared; final CI/review and owner visual acceptance pending

## Owner scope

After accepting homepage/contact/leadership updates locally, the owner supplied member-home screenshots and authorized a clearer member space: membership validity, applications/documents, profile/portrait/renewal actions and mobile presentation. This increment updates member home and the shared private header/styles, not business decisions, admin powers, payment or issuance rules.

## Behavior

The home dashboard displays each own membership period, preserving the existing state and interpreting active periods against the same policy date used by documents: future starts are Upcoming, end dates are exclusive, and suspended/cancelled states take precedence. Permanent terms explicitly have no end date. Renew action eligibility reuses the existing RenewalForm queryset. Application submission availability does not grant permission or bypass commands.

Pending application totals are own-profile only. Document totals and the existing document list share one ownership query including the already-supported guardian/minor scope and institutional documents. Totals are historical record counts, not claims that every credential is currently valid. All per-document access guards remain unchanged. Other members' names, terms and documents are excluded. Existing no-store, login, CSRF logout, locale and owner-testing gates are retained.

Use local Arabic UI fonts and scoped private dashboard styling, navy/teal/gold, responsive cards, visible statuses and quick links. The shared private base keeps existing forms/navigation destinations, adding a styled header and main landmark. No schema migration or issued artifact changes.

## Evidence

Regression tests cover current/upcoming/exclusive-expired/suspended periods across AR/FR/EN, private totals, empty accounts, permanent terms, escaped identity and login/logout boundaries. Existing account and CSRF membership journeys are included. System/migration/metadata/content checks, PostgreSQL CI and exact-head Codex review precede merge. Browser installation was unavailable for this environment in the previous increment; desktop/mobile visual acceptance remains with the owner. Local latency remains deferred and no performance claim is made. Hosted deployment, costs, Tighri and MHIOS are untouched.
