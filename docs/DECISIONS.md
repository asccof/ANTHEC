# Decision register

| ID | Status | Decision | Basis / next evidence |
|---|---|---|---|
| ADR-001 | Authorized | ANTHEEC independent from MHIOS | Current user instruction |
| ADR-002 | Authorized boundary | No production, paid services or real-person data | Current user instruction |
| ADR-003 | Existing baseline | AR/FR/EN; membership never automatically grants accreditation | Executive §§1,3–5 |
| ADR-004 | Proposed, PoC required | Django/PostgreSQL/Wagtail modular monolith | Executive §11; prove CMS workflows first |
| ADR-005 | Proposed engineering design | Atomic decision/outbox, idempotency scoped by action and payload hash | Detailed §§3,8; prove concurrency and crash recovery |
| ADR-006 | Awaiting business approval | Validity boundaries, leap day, early renewal, campaign expiry | F04/F06; no production defaults |
| ADR-007 | Awaiting privacy approval | Public verification fields and serial lookup restriction | F09/F14/F15 |
| ADR-008 | Deferred | Tighri integration, payments gateway, WhatsApp, branch accounts | No integration contract; Executive §§7,9,14 |

Changing a decision requires a dated entry with rationale, affected requirements and tests. This is an engineering log, not an assertion of external approval.

2026-10-10 technical evidence: Django 5.2.18 / Wagtail 7.4.3 LTS / psycopg 3.3.6 pinned, Python 3.12. Compatibility and content-locale approach checked against https://docs.wagtail.org/en/v7.4/releases/7.4.html and https://docs.wagtail.org/en/v7.4/advanced_topics/i18n.html. PostgreSQL 16 CI required; this is development evidence, not production architecture acceptance. All dependencies are open-source; package license metadata must be included in the next dependency audit.
