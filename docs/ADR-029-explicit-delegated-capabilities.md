# ADR 029: Explicit independent delegated capabilities

Date: 2026-10-18
Status: Implemented locally; PostgreSQL/container/recovery CI, exact-head review and owner acceptance pending.

## Owner decision

The owner explicitly authorized per-account checkbox grants for each existing action, with view, approval, rejection, execution, editing, suspension, cancellation and reactivation kept independent. Primary identity, delegation management, user/group/security administration and technical secrets stay primary-only. Explicitly authorized signing asset delegation supersedes the former primary-only signing upload/review restriction.

## Boundary

`governance/capabilities.py` is the closed catalog and action-to-capability resolver. All operational commands authorize under the existing Authority lock before idempotency lookup, resolving exact decision/state and cumulative capabilities for compound updates. Explicit view prerequisites are validated, never auto-selected. Independent accreditation review cannot change criteria/assessment/fee without edit; reopening is separate. Partner state/content/public visibility changes require each affected capability. Membership tier-three linked issuance remains the existing indivisible policy operation.

Administrative reads, private image endpoints, document preview/download/generation and business forms enforce separate scopes. Own-member and guardian self-service rights remain ownership-based. Membership-only views omit payment/refund proofs and document records; activity-only views omit registrations and attendance. UI visibility is a convenience; server checks remain decisive.

CMS delegates use per-delegation permission groups, a resolved-name allowlist and exact POST checks. Unrelated Django permissions cannot widen it. Unknown admin/API routes, user/group/security settings, workflows, schedules, copy/move/revert and other unsupported advanced CMS operations remain primary-only. A publisher can publish an existing saved revision without edit; stale revision selection is rejected. Raw edit-and-publish requires both edit/create and publish. Contact and public image/file scopes are distinct from private portraits and signing rasters.

## Transition and sessions

Migration 0012 adds a default-empty capability list, disables every legacy broad delegation, increments its epoch and removes the old shared CMS group grant. There is no automatic full-access conversion or rollback restoration of broad access. Primary authority is unchanged. Reassign explicit scopes through the director page, then reauthenticate the delegate. Every edit/revoke increments the epoch and records before/after scopes, target identity, actor and reason. The HTML form includes expected epoch to prevent stale owner edits overwriting newer scope choices.

## Validation and deployment limits

Tests cover independent decisions and compound mutations, forged JSON/direct admin routes, unrelated permissions, read-only disclosure, document actions, signing access, missing/unknown scopes, session/replay revocation, saved-revision publishing, stale editor forms and legacy closure. PostgreSQL tests additionally cover parallel stale edits and revoke/authorization serialization. Final evidence belongs in the PR. No hosted deployment, paid resources, release gate changes or Tighri modifications. Owner desktop/mobile and real delegated-login acceptance remain pending.
