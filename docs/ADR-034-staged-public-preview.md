# ADR034 — Staged public preview and workflow kill switches

Date: 2026-10-21. Owner authorized preparation after accepting login to the hosted PR53 version. The existing service must remain private during this increment. Public launch, real-data readiness, paid resources and Tighri changes are not implied.

## Decision

Add `public-preview` to secure hosted settings, alongside unchanged `owner-testing`. It is a read-only editorial preview, not operational production. Only GET/HEAD of locale CMS pages, the public activity catalogue/details/images and approved visible partner listings are available anonymously. Unknown endpoints, member accounts, applications, partnership submissions, participation, document verification/downloads and private assets remain denied. The current primary-only administrative boundary, factor at login, session epoch, global login ceiling and CSRF checks are preserved. Public routes do not bypass publication, visibility or record authorization in their views. Responses remain no-store/noindex; no search indexing or full launch is claimed.

The public preview requires an explicit operator acknowledgement that published CMS content, activity text/images/links and visible partners have been reviewed. This setting is an operational acknowledgement, not an automated legal/security certification. Content in the hosted database can differ from local UAT content. No data is copied from Windows or automatically published.

Independent application, payment and issuance guards now also consult their own switch, before command writes/replays. Self-service profile commands and account signup receive the application guard. Existing owner-testing restrictions override switch values. Local synthetic development/test behavior remains enabled by default. Both hosted modes reject any nonzero/malformed workflow configuration, including `1`: real transactions cannot be enabled by mistakenly changing one environment variable. A later independently governed operational mode is required after release gates are evidenced. This increment intentionally does not implement that operational mode or electronic payments.

## Configuration and eventual rollout

| Variable | Existing private service | Prepared editorial preview |
|---|---|---|
| `DJANGO_SETTINGS_MODULE` | `antheec_app.settings.production` | same secure module |
| `ANTHEEC_MODE` | `owner-testing` | `public-preview` |
| `ANTHEEC_PUBLIC_CONTENT_APPROVED` | unused | exactly `1`, only after content audit and an explicit decision to expose it |
| `ANTHEEC_APPLICATIONS_ENABLED` | absent or `0` | absent or `0` |
| `ANTHEEC_PAYMENTS_ENABLED` | absent or `0` | absent or `0` |
| `ANTHEEC_ISSUANCE_ENABLED` | absent or `0` | absent or `0` |

Do not set these preview variables on Render during preparation. Do not change secrets, database namespace, plan, worker count, backup key, network access, disabled filesystem uploads or dummy email backend. Private database-backed editorial images keep their existing publication/authorization rules. Gemini configuration and private key are not copied from the owner's local machine.

Before an eventual preview exposure: verify exact reviewed commit/CI, current live source and settings; retain a fresh backup with its original encryption key held separately; audit published content on the hosted instance; obtain the distinct owner decision to expose the preview; deploy and verify public GET/HEAD, blocked submissions and primary login. Login entry is `/admin/login/`, not the anonymous `/admin/` URL. Hide disabled member/application/verification/participation links and show AR/FR/EN preview notices.

Revert exposure by setting `ANTHEEC_MODE=owner-testing` and redeploying the same compatible code; verify anonymous denial. This is access-mode rollback, not a database restore. Do not remove migration columns, restore old broad delegations, rotate keys or blindly deploy pre-migration code. This increment has no schema migration.

## Validation and remaining gates

Regressions cover multilingual editorial access, hidden closed links, denied private/unknown routes and POSTs without domain writes, unpublished activities, primary factor/nonprimary denial, CSRF/login budget, service-level fail-closed behavior, independent guards and secure configuration rejection. Existing private, public-presentation and content tests remain required, plus metadata/system/drift/dependency checks, PostgreSQL/container/recovery CI and exact-head external review. Record final evidence in the PR rather than declaring it before execution.

The owner reports a fresh backup downloaded and successful hosted login after PR53 deployment `1487da5` (`dep-dbcbfloae00c7397l3o0`); initial health/login/static checks succeeded. This does not prove hosted restoration/decryption, legal/privacy acceptance, long-term stability or capacity. Latency measurement is explicitly deferred at the owner's request; its network cause is unproven. POL-01–08, artwork, delegated action scopes and participation NOT ISSUED semantics are unchanged.
