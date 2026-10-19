# ADR032 — Owner-authorized optional free-tier editorial translation

Date: 2026-10-19. Status: owner-authorized scope; implementation and synthetic testing prepared. Required CI/review and actual provider/owner acceptance remain separate PR evidence.

## Decision and scope

The owner approved Google Gemini's free API for infrequent activity editorial translation. This amends ADR008/AGENTS historical external-translation deferral only for public activity text intentionally submitted by an authorized editor. It authorizes no paid account, billing activation, Render deployment, extra worker, Tighri change or public release. Existing CMS/manual translations are not silently converted and no visitor request triggers translation.

The activity editor selects the source AR/FR/EN locale and confirms the text is intended for public publication, contains no private data and will be sent to Google. A description and title are required. Translate-and-preview fills editable fields without saving/publishing an activity; save can retain a draft, and accept-and-publish uses ordinary scoped commands. Translate-and-publish explicitly skips review but runs the same validations, authorization and atomic create/update/media/publish sequence. Existing target text (including manual edits) requires explicit replacement; normal saves never regenerate. Source changes are not automatically sent. A newly generated or manually edited translation is persisted with the activity on save and is never regenerated on page visits.

Only the selected locale's nonempty title, summary, description, programme, audience, speakers and public location are sent. Never send participant lists, contact data, private consent, administrative reasons, uploads, portraits/signatures, documents, URL contents or database context. Text may itself contain personal data; the editor must keep private/case information out. Free-tier content can be used by Google to improve products, hence this is public-editorial-only, not a clinical/private-data translator.

## Provider, resource and failure boundary

A fixed Gemini Developer API HTTPS origin/model (gemini-3.5-flash-lite), API-key header, strict JSON schema, bounded input (8000 total source characters), bounded 200KB streamed response and 8192 output tokens. Two locales in one request, no SDK dependency, redirect, retry, fallback model, tools, URL retrieval or paid fallback. Connect/read timeout is 5/30 seconds (read timeout is idle time, not an overall job deadline). Failure, refusal, incomplete response or malformed/oversize output never publishes partial text; raw provider errors/key are not returned or logged by this module. All provider output is checked against editorial field/locale bounds and still escaped at display.

Authority-locked reservation limits generation to 20 attempts per UTC day globally, including failures. No network while holding database/Authority locks. Reauthorize before returning/persisting successful generated output; stale epochs/revoked/inactive users cannot finish a publish. Persist attempt actor/key/hash/state/output, not a duplicate source text or provider/key response. Same actor/key/source replay returns cached completed output; pending/failed attempts do not resend automatically. Cached results expire after 30 days and are pruned on the next authorized generation; published activity text and audit history are unaffected. A failed editor form receives a fresh generation key for explicit retry. This is a technical cache duration, not a new records-retention policy. Global caps and idempotency survive worker restarts via PostgreSQL.

Generation requires activity.view plus create/edit, with activity.publish additionally for live edits or direct publication. Existing explicit view prerequisites apply. Saving and publication recheck current scoped authorization, audit, epoch and idempotency. No newly inherited delegation permissions. Existing publication description prerequisite and frozen participant consent/date conditions remain.

Migration0014 adds TranslationAttempt. Runtime defaults disabled. Operator must configure all three environment settings: ANTHEEC_GEMINI_ENABLED=1, ANTHEEC_GEMINI_FREE_PROJECT_CONFIRMED=1, ANTHEEC_GEMINI_API_KEY privately. The confirmation flag is an operator acknowledgement, NOT technical detection of Google's billing state: the owner must verify the Google project has NO linked billing account. Keys alone cannot prove a project is free. Do not enable a billed project, create credentials on the owner's behalf or paste keys into chats/repository. No key has been supplied and no live provider translation has been verified in this increment.

## Sources checked 2026-10-19

- https://ai.google.dev/gemini-api/docs/pricing — 3.5 Flash-Lite standard free tier; free data-use distinction.
- https://ai.google.dev/gemini-api/docs/models — current model identifier.
- https://ai.google.dev/gemini-api/docs/structured-output — schema constrained generation (validated again by application).
- https://ai.google.dev/api/generate-content — fixed REST request/response contract.
- https://ai.google.dev/gemini-api/docs/api-key — private key setup/header.

Quota/model availability can change. Do not claim a guaranteed daily provider allowance. Local mocked provider tests validate our boundary, not actual translation quality, provider eligibility or account configuration. Owner real-key AR/FR/EN editorial UAT remains required before calling this operational.
