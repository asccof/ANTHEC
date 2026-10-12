# ANTHEEC engineering instructions

- ANTHEEC is independent of MHIOS; never import its code, governance, credentials or data.
- Work on bounded branches and PRs. Re-read live repository state and these instructions before writes.
- Owner authorization on 2026-10-12 permits preparation for isolated, owner-only Render testing with synthetic data. It does not authorize paid resource creation, deployment, external translation/email delivery, real-person data, clinical records, public launch or merging production changes.
- Original source attachments and detailed accreditation criteria are private; do not commit them to this public repository.
- Synthetic examples use `example.invalid`. Never commit `.env`, uploads, databases, credentials or tokens.
- Keep `docs/STATUS.md`, source traceability and ADRs honest: prepared, tested, externally reviewed and accepted are different states.
- Run metadata validator, metadata unit tests, Django system checks, migration drift checks and content tests for this increment. PostgreSQL CI evidence is required before calling database compatibility validated.
- Owner-approved POL-01–08 in docs/APPROVED_POLICIES.md supersede conflicting historical proposals. Third-tier approval/renewal must atomically grant linked professional accreditation and separate gold card/certificate; lower tiers do not. Do not invent further organizational decisions.
- Production settings may support explicit `owner-testing` only; public production, external registration/applications, payments and official document issuance remain blocked. Participation remains a NOT ISSUED visual proof. Preserve the approved card/certificate artwork and POL-01–08. Never modify, restart, migrate or deploy Tighri.
