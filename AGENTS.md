# ANTHEEC engineering instructions

- ANTHEEC is independent of MHIOS; never import its code, governance, credentials or data.
- Work on bounded branches and PRs. Re-read live repository state and these instructions before writes.
- No production deployment, paid services, external translation/email delivery, real-person data or clinical records.
- Original source attachments and detailed accreditation criteria are private; do not commit them to this public repository.
- Synthetic examples use `example.invalid`. Never commit `.env`, uploads, databases, credentials or tokens.
- Keep `docs/STATUS.md`, source traceability and ADRs honest: prepared, tested, externally reviewed and accepted are different states.
- Run metadata validator, metadata unit tests, Django system checks, migration drift checks and content tests for this increment. PostgreSQL CI evidence is required before calling database compatibility validated.
- Owner-approved POL-01–08 in docs/APPROVED_POLICIES.md supersede conflicting historical proposals. Third-tier approval/renewal must atomically grant linked professional accreditation and separate gold card/certificate; lower tiers do not. Do not invent further organizational decisions.
- Production settings must remain blocked until separately authorized.
