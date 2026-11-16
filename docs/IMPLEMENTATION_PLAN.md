# Implementation and verification record

This historical record describes the five-stage delivery and the checks recorded on **13 November 2026**. The stages were originally submitted as stacked pull requests. The cumulative [v1.0.0 integration PR](https://github.com/cstrava/ai-helpdesk/pull/6) targets `main`; current release checks are recorded separately in [Release verification](RELEASE_VERIFICATION.md). This document is not a live CI status page.

Setup and recovery procedures are maintained in [Operations](OPERATIONS.md), endpoint behavior in [API](API.md), and model results in [ML evaluation](ML_EVALUATION.md).

## Delivery stages

The starting point was `feature/data-pipeline` at `8474796`. Its recorded CI result was 31 backend tests, 7 frontend tests and 2 browser cases, with lint and build passing. Those counts describe the earlier version. The recorded PR chain was #1 → #2 → #3 → [#4](https://github.com/cstrava/ai-helpdesk/pull/4) → #5, each based on the preceding branch.

| Stage | Implemented behavior | Recorded verification |
|---|---|---|
| 1. Reliability | Recover a ticket after a lost confirmation response; preserve unsent messages and edited drafts per account/conversation in session storage; clear unsaved content on logout; reject incompatible legacy schemas | `fix/application-reliability`: 43 backend, 19 frontend and 4 browser cases; lint, typecheck and build passed. [PR #1](https://github.com/cstrava/ai-helpdesk/pull/1), [CI run](https://github.com/cstrava/ai-helpdesk/actions/runs/43454447275) |
| 2. Ticket collaboration | Public replies, support-only internal notes, idempotent messages, version-checked assignment, resolution messages and reopening reasons | `feat/ticket-collaboration`: 54 backend, 22 frontend and 4 browser cases; lint, typecheck and build passed. [CI run](https://github.com/cstrava/ai-helpdesk/actions/runs/43462307139), [follow-up run](https://github.com/cstrava/ai-helpdesk/actions/runs/43462355989) |
| 3. Support workspace | Combined filters, user-declared impact, audited support priorities, a descriptive dashboard and persistent notifications | `feat/support-workspace`: 56 backend, 23 frontend and 4 browser cases; lint, typecheck and build passed. [CI run](https://github.com/cstrava/ai-helpdesk/actions/runs/43466142551), [follow-up run](https://github.com/cstrava/ai-helpdesk/actions/runs/43466211044) |
| 4. ML feedback and evaluation | Explicit category review, invalidation after relevant edits, minimal support-only CSV export and reproducible evaluation; no retraining or model replacement | `feat/ml-feedback-evaluation`: 57 backend, 24 frontend and 4 browser cases; lint, typecheck, build and Docker image builds passed. [CI run](https://github.com/cstrava/ai-helpdesk/actions/runs/43474446987), [follow-up run](https://github.com/cstrava/ai-helpdesk/actions/runs/43474500679) |
| 5. Integration and documentation | Full workflow on desktop/mobile emulation, fresh migrations and upgrades, Nginx integration, restart persistence and real Romanian/English model checks | `feat/portfolio-verification`: local checks described below. [PR #5](https://github.com/cstrava/ai-helpdesk/pull/5), [CI run](https://github.com/cstrava/ai-helpdesk/actions/runs/43477226299), [follow-up run](https://github.com/cstrava/ai-helpdesk/actions/runs/43477234706) |

## Integration checks recorded on 13 November

A temporary Compose project, `ai-helpdesk-portfolio-verify`, used its own PostgreSQL volume, API on `127.0.0.1:8004` and Nginx/frontend on `127.0.0.1:5176`. It did not migrate or use the personal application database. It shared the existing local Ollama service for inference only.

The recorded checks covered:

- Nginx forwarding for health, authentication, conversation, draft, ticket, collaboration, review and export endpoints.
- A real Romanian workflow using Qwen `qwen3:4b-instruct` and XLM-R v2: conversation, editable draft, classification, confirmation, ticket recovery, support assignment, public reply, private note, resolution, reopening, explicit review and CSV export.
- A real English workflow through conversation, draft, classification, confirmation and ticket recovery. These real-model proxy checks used an HTTP client rather than browser automation.
- After restarting the temporary API, healthy status and Nginx health forwarding returned, and the volume retained three synthetic tickets and three conversations. Earlier stage 1–2 smoke checks also verified session persistence across API restart.
- A fresh database recorded migrations 001–007. The 57-test backend suite covered legacy adoption, upgrades and repeated migration, including preservation of existing text, model versions and unassigned historical records.
- Desktop Chromium and Pixel 7 emulation, dialog keyboard focus, Escape, and targeted contrast checks. This was not a complete accessibility audit.

The automated suite uses real HTTP, authentication and SQL with simulated Qwen/XLM-R inference. In particular, the confirmation-recovery browser case commits a ticket in the backend, replaces its response with HTTP 502, and verifies recovery without a second confirmation POST. These tests validate application behavior; they do not measure model quality. Temporary integration services were stopped without deleting their volume; the personal database and services were not upgraded to the cumulative version during these checks.

## Engineering decisions and tradeoffs

- **Human confirmation before creation.** Drafts remain editable, and classification runs on the confirmed text. Qwen can repeat questions or generalize details, so generated text is not accepted automatically.
- **Database constraints plus recovery.** Row locking and a unique conversation-to-ticket relationship prevent duplicate creation. The frontend reads the committed ticket after an ambiguous response instead of assuming failure.
- **Optimistic concurrency for support actions.** Version checks reject stale assignments or status edits rather than silently overwriting another support user's changes.
- **Historical ownership remains unknown.** Legacy records are not assigned to a guessed account. Ordinary users cannot access unowned records; support can administer historical tickets, while unowned conversations are not exposed.
- **Separate inference responsibilities.** Ollama runs Qwen for conversation and draft generation. The API runs the existing XLM-R v2 classifier on CPU; the Compose GPU reservation belongs to Ollama. The delivery did not retrain or replace model weights.
- **Explicit ML review.** A category change alone is not an approved evaluation label. Review is a separate action, becomes invalid after relevant edits, and exports only the documented fields.
- **Isolated tests.** Automated database tests use `ai_helpdesk_test` and temporary schemas. Real-model smoke tests used separate temporary databases. Personal application data is not a test fixture.

## Earlier baseline: 9 November

The earlier delivery introduced authentication, revocable sessions, CSRF checks, account-owned conversations, confirmed ticket creation, audit events and a migration runner. Its final local record was 31 backend tests, 7 frontend tests and 2 browser cases, plus lint, frontend build, Docker builds and Nginx health forwarding. Remote CI had not run at that point; a later [baseline CI run](https://github.com/cstrava/ai-helpdesk/actions/runs/43449306371) passed.

A subsequent local application upgrade on that date was preceded by a PostgreSQL backup and an isolated restore comparison. The recorded comparison preserved 7 conversations, 32 messages and 3 tickets while applying migrations 001–004; historical owners remained null. These figures describe that specific local upgrade, not a reusable benchmark or the current database contents.

## Verification limits and next steps

Real-model smoke checks used a small number of synthetic examples. Qwen sometimes requested details already supplied and generalized wording; inspecting and editing drafts remains necessary. The separate [ML evaluation](ML_EVALUATION.md) identifies each model version and dataset and explains why its pilot scores do not establish general ticket-classification performance.

The browser runs covered Chromium desktop and Pixel 7 emulation, not Safari, Firefox or a physical phone. Targeted keyboard and contrast checks do not replace an accessibility audit. Dashboard and notification behavior has backend coverage; the browser suite is not exhaustive coverage of those views.

Remaining work includes independent, larger ML evaluation; broader browser and accessibility checks; and account recovery, email verification and MFA if the application is extended beyond local demonstration. No public deployment or operational track record is claimed here.
