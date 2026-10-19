# ADR 030: Primary login MFA and password-only delegated sessions

Date: 2026-10-19
Status: Implemented locally; final CI, exact-head review and owner acceptance pending.

## Owner decision

The owner explicitly amended POL-04: only the primary director supplies an administrative second factor, once at each login. Delegates sign in with their own username/password. No five-minute operation timer or repeated OTP during work. Initial primary enrollment and one-use recovery remain available; no primary factor bypass.

## Superseded contract and acceptance instructions

README.md now documents the role-specific login/workspace flow and removes timed operation reauthentication. DOMAIN_CONTRACTS.md now defines the amended authentication contract and scoped grants; OWNER_ACCEPTANCE_AR.md UAT-11 now tests primary-login-only MFA, password-only delegates, permitted/forbidden actions and epoch revocation. DECISIONS.md retires the old timer constant. Earlier phase documents and ledger snapshots describe historical behavior and do not override this owner decision. Actual hosted deployments are unchanged until separately authorized and verified.

## Implementation

An actual Django login signal clears prior administrative/OTP state. The primary earns epoch zero only after factor verification. An active delegate receives the current valid explicit-grant epoch at password login, including the native Wagtail login boundary. Grant changes never upgrade existing sessions: the delegate must sign out and sign in. Every operation still checks current active account, grant, exact capabilities and session epoch under the Authority lock; CSRF, primary-only actions, audit and revocation remain unchanged. Existing verified primary sessions remain valid until their normal logout/expiry/password invalidation. The recent argument remains as a compatibility parameter but no longer imposes time-based reauthentication.

The shared navigation exposes Administrative workspace only to the primary or an active delegate. Member password login sends directors to the appropriate workspace or primary challenge. Delegate security/enrollment endpoints cannot create administrative OTP requirements. The owner-testing hosted gate remains primary-only and unchanged; this does not open hosted delegate access or authorize deployment.

## Verification

New HTTP regressions cover password-only delegate login, permitted/denied workspace links, epoch changes, grant-after-login, revocation, ordinary-member denial, primary login factor and repeat login clearing factor state. Prior timer-denial regressions now test revoked epochs instead. Final PostgreSQL/container/recovery and external review evidence belongs in the PR. No schema change, Tighri changes, paid resources or deployment.
