# ADR 037 — exact canonical origin and legacy QR continuity

Date: 2026-10-23. Authority: owner purchased anthecmaroc.com and requested completion of launch on existing ANTHEC resources. Status: prepared; exact-head CI/review and runtime cutover are separate evidence.

Keep one canonical HTTPS origin for CSRF, administration and newly generated QR URLs. An optional distinct exact `ANTHEEC_LEGACY_ORIGIN`, operational mode only, permits the previous hostname solely for GET/HEAD redirects (308) to the canonical origin. Redirects preserve the encoded path/query and omit a Location fragment so browsers inherit existing QR fragments. Reject unsafe legacy-origin methods with 421 before authentication/business handling. Retain the health endpoint on either exact host; reject all unlisted hosts. No wildcard, secret/key rotation, asset/PDF rewriting or change to public verification policy.

An explicit `ANTHEEC_SYNC_SITE_ORIGIN=1` predeploy step aligns only the single default CMS site's hostname/HTTPS port. The command has a read-only plan, operational-only apply, collision checks and idempotent updates. Page content, publication receipts, membership and issued documents stay unchanged.

An explicit `ANTHEEC_PUBLIC_DISCOVERY_ENABLED=1` permits successful anonymous public editorial GET/HEAD responses to be indexed. Errors, redirects, authenticated responses, accounts, verification and administration remain noindex. All dynamic responses retain no-store. Preview modes reject activation; source deployment alone enables neither cutover nor discovery. DNS/TLS ownership does not establish application or legal acceptance.

Sequence: confirm DNS/TLS for apex and www; pass protected-PR CI/review; merge; atomically set canonical/legacy origins and the two flags in existing service configuration, which triggers the single deployment; verify both origins, www redirect, languages, notice/forms, CMS origin, privacy headers and legacy fragment continuity. Keep Render subdomain enabled. If runtime acceptance fails, restore previous canonical origin and clear legacy/discovery/sync settings together. Never touch Tighri, add paid resources or publish internal review/backup materials.
