# ANTHEEC implementation backlog

2026-10-10. No milestone here authorizes deployment or real-person data.

| Task | GitHub | Dependency / acceptance gate | Current state |
|---|---|---|---|
| ENG-001/003 | #1 / PR #2 | Source baseline + executable multilingual CMS PoC; PostgreSQL CI and reviewed head | Implemented; Codex findings being resolved; full CMS acceptance pending |
| ENG-002 | PR #2 | Independent GitHub history/CI/review; branch protection status separately checked | GitHub available; protection API inaccessible to integration, not claimed configured |
| ENG-004 | #3 | Domain contracts, least-privilege matrix, data dictionary, transactions and test scenarios | Draft delivered in this documentation increment |
| ENG-005 | #5 | #3 + PR #2; translation orchestration, administrative MFA/roles, CMS/media | Planned |
| ENG-006 | #6 | #3 + #5; membership/payment/document outbox; calendar/pricing decisions | Planned |
| ENG-007 | #7 | #3 + #6; separate accreditation, bounded validity, private criteria/fees | Planned |
| ENG-008 | #8 | #3 + #5/#6; eligibility/capacity/invitation/attendance | Planned |
| ENG-009 | #9 | #3 + #5; partnership requests/publication/branches | Planned |
| ENG-010 | #10 | #5–9; all original acceptance criteria, security, backup restore, performance and training | Planned, non-production |
| ENG-011 | Not commissioned | Separate approval after readiness | Production, paid services and real records blocked |

Each issue specifies scope, dependency, acceptance and unresolved owner policies. Priority is #3 contracts + #5 identity/CMS before business workflows. Do not treat the metadata/CMS test count as complete platform acceptance.

Policy review items POL-01–08 are defined in DOMAIN_CONTRACTS.md and traced to the original inception findings. The contracts are proposals, not a claim of owner approval.
