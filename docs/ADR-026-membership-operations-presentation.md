# ADR 026: Membership operations presentation

Date: 2026-10-18
Status: Prepared; exact-head review and PostgreSQL CI pending.

The owner accepted the member dashboard and authorized continuing the administrative presentation. Membership requests were dense lines; financial totals and administrative commands lacked visual hierarchy.

Use localized request cards with explicit status and the existing latest-100 ordering. Separate identity, financial totals, intake, decisions, membership, documents and history. Scope responsive styling to membership administration. Use explicit payment, exemption, refund, membership state and document reissue captions. Keep bound errors visible and retain every POST action, CSRF token and existing authorization/service validation. No schema, policy, artwork, signing assets or hosted deployment changes.

Owner screenshots informed the layout. Desktop/mobile visual acceptance remains an owner UAT step; automated browser screenshots are not claimed. Final checks and external review evidence will be recorded in the PR before merge.
