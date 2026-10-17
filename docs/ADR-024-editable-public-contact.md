# ADR-024 — Editable public association contact

Date: 2026-10-17
Status: prepared; final checks, exact-head CI and review pending

## Owner authorization

The owner explicitly supplied the public association telephone/WhatsApp number and Rabat address and requested editable administration fields. The same phone drives both call and WhatsApp links. The official email is intentionally unspecified: display its localized heading without a dummy mailbox or mailto link until the administrator supplies it. Owner-approved public contact is distinct from the synthetic-only applicant/test data boundary; private account/profile contact is never used.

## Implementation

Wagtail site settings provide public phone, AR/FR/EN address and blank optional official email. Defaults use only the owner-authorized public number/address; Latin address spellings are editable transliterations. Data is shown in the homepage contact section and institutional-page footer. Editing uses existing administrative authority/MFA middleware, Wagtail site permissions, CSRF and setting edit logging. No public form or external delivery is added. Wagtail contrib.settings is enabled and content migration 0003 creates one configuration per Site.

Public GET reads configuration without creating rows; absent configuration uses unsaved owner defaults. A single validated phone normalizes Moroccan local format to +212 for tel and wa.me. Values remain template-escaped; phone/email are revalidated before generating links, even for rows written outside the form. Empty phone suppresses both phone/WhatsApp links. Email heading remains as the requested placeholder until a valid address is saved. No maps, chat widgets, external resource requests or messages are sent by the server.

## Validation and limits

Tests cover locale output, read-only public GET, same-number normalization, admin update reflected in footer, escaped addresses, invalid persisted links, blank mailbox, authority/MFA and CSRF. Required metadata/system/migration/content checks and PostgreSQL CI precede merge. Owner local visual acceptance and hosted deployment remain pending. No card artwork, payment/issuance/public-launch gate, costs, Tighri or MHIOS changes.
