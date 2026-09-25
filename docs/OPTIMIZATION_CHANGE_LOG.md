# Ragverse Optimization Change Log

This journal records the reasoning, implementation, verification, and production evidence for the zero-cost optimization rollout started on 2026-09-25.

## Goals

- Reduce query latency and avoid unnecessary free-tier database/API usage.
- Keep synchronous SDK and document work from blocking FastAPI's async event loop.
- Make streamed answers reliable across arbitrary network packet boundaries.
- Prevent stale retrieval-cache results and unbounded in-process memory growth.
- Reduce ingestion cost without changing Ragverse's supported source types.
- Preserve backward compatibility while database migrations deploy.

## Changes and reasons

### Retrieval and database traffic

- Added `002_query_optimizations.sql` with `match_document_chunks_for_docs`, which retrieves per-document candidates in one Supabase RPC instead of one sequential RPC per active document.
- Added a compatibility fallback that still uses one existing `match_document_chunks` call while the new RPC is unavailable during rollout.
- Added `append_chat_message`, combining message insertion and session timestamp update in one database transaction/request.
- Removed the redundant session upsert inside every message insert. A query now ensures its session once, then appends its user and assistant messages.
- Batched document-chunk upserts in groups of 50 to avoid oversized free-tier HTTP requests.
- Added a migration ledger and PostgreSQL advisory lock so migration files are applied once and concurrent application starts cannot race.

Expected result: fewer network round trips before an answer begins, lower Supabase request volume, and safer startup migrations.

### FastAPI concurrency

- Moved synchronous document parsing, URL fetching, embeddings, vector operations, Supabase operations, and persistence calls to Starlette's worker threadpool.
- Changed authentication endpoints to synchronous route functions so FastAPI schedules bcrypt/database work in its threadpool.

Expected result: one slow upload, provider call, or database request no longer blocks unrelated requests on the main async event loop.

### Provider reuse and streaming safety

- Cached chat and embedding wrapper instances by provider/model configuration so their setup and HTTP clients can be reused.
- Prevented provider fallback after a stream has already emitted content. A mid-stream fallback could otherwise append a second answer after a partial first answer.
- Replaced silent embedding truncation/zero-padding with exact dimension validation. Vectors from different embedding spaces must not be mixed in one index.

Trade-off: if the configured primary embedding provider fails and a fallback emits a different dimension, ingestion/querying now fails clearly instead of returning misleading similarity results.

### Retrieval cache

- Changed the local cache key to include normalized question text and the active-document set.
- Added a 10-minute TTL, a 32-query-per-session limit, locking, and document/session invalidation.
- Exact cache hits are reused; chunks scored for an older question are no longer excluded from retrieval for a new question.

Expected result: correct query-specific retrieval and bounded memory usage.

### Frontend streaming and request reduction

- Rebuilt the SSE-shaped response parser with a carry-over buffer and streaming `TextDecoder`, so JSON events split across network packets are preserved.
- Batched token UI updates every 40 ms rather than rerendering for every model token.
- Limited submitted history to the latest eight messages.
- Removed per-token `localStorage` serialization and reduced smooth-scroll work.
- Removed redundant active-document refresh requests after successful activate/deactivate operations.
- Delayed chat/active-document restoration until the latest session ID is resolved, avoiding duplicate initial requests.

Expected result: smoother long answers, fewer browser/database requests, and no intermittent lost stream fragments.

### Ingestion and dependency footprint

- Limited image description work to eight unique images per document and skipped images smaller than 2 KB. Both limits are configurable.
- Switched chunk IDs to SHA-256 over full content plus a document-wide chunk index, preventing collisions across pages with similar openings.
- Preserved correct one-based PowerPoint slide metadata.
- Removed unused direct requirements: `pandas`, `networkx`, `msoffcrypto-tool`, and `pillow`. Transitive dependencies can still install them if another package genuinely requires them.
- Failed metadata persistence now fails the upload and triggers best-effort cleanup instead of silently returning an apparently successful but incomplete document.

Expected result: fewer vision calls, smaller installation footprint, stable chunk identity, and fewer partial documents.

## Verification

### Local

- Frontend ESLint: passed.
- Frontend Vite production build: passed.
- Git whitespace/error check: passed.
- Backend Python 3.12 compilation: passed using an official temporary portable runtime.
- Backend application import and route construction: passed (10 routes loaded).
- Existing upload/URL guardrail suite: passed all positive and negative checks.
- New optimization checks: passed chunk-ID uniqueness, query-specific cache behavior/invalidation, and embedding-dimension validation.
- Environment note: the existing `backend/denv` still references a deleted Python 3.12 installation and should be recreated for normal local development.

### Production

- Optimization commit: `036828a` (`Optimize retrieval streaming and ingestion`), pushed to `origin/production`.
- Render health endpoint: HTTP 200 with `{"status":"ok"}` after deployment.
- Public Vercel UI: reachable and rendered the sign-in screen.
- Deployed Vercel bundle: confirmed to contain the new streaming `TextDecoder` buffer path and no old `ragverse_chat_messages` per-token local-storage path.
- Existing disposable QA login: passed.
- Workspace restoration: 9 documents, latest session, 30 pre-check messages, and 1 active document restored.
- Live document-backed query against `sample1.pdf`: HTTP 200, SSE `[DONE]` received, 1 source returned, and a 106-character answer completed in 12.1 seconds.
- Answer accuracy: returned `The main identifying fact in the active document is that the project codename is Violet Harbor [Source 1].`
- Persistence check: latest assistant message and its single source were restored from production after the stream; total history increased to 32 messages.

## Intentionally deferred

- An approximate pgvector index was not added in this rollout. The current vectors are 3,072 dimensions, and changing the storage/index representation safely requires a planned re-embedding migration and retrieval benchmark against existing production data.
- The stale 923 MB `backend/denv` folder was not deleted automatically. It is ignored by Git and contains local-only files; recreate it first, then remove it as a separate local cleanup.
