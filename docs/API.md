# API and access rules

OpenAPI is available at `http://127.0.0.1:8000/docs` when the API is running. Nginx exposes the same routes under `/api` for the frontend; direct API requests omit that prefix. This document describes the implementation in this checkout, including migrations 001–007.

## Authentication

`POST /auth/register` creates a `user` account. `POST /auth/login` sets the `helpdesk_session` HttpOnly cookie and returns the account identity and `csrf_token`. `GET /auth/me` retrieves the current session; `POST /auth/logout` revokes it.

Authenticated writes require the cookie and `X-CSRF-Token` header. If an `Origin` header is present, it must match `APP_ORIGIN`; requests marked `Sec-Fetch-Site: cross-site` are rejected. Registration and login also apply the origin checks. Each is limited to 30 requests per ten-minute window per direct network peer. Proxy headers are not trusted, so users behind the local Nginx proxy share a rate-limit bucket.

## Conversations and ticket confirmation

| Endpoint | Access and behavior |
|---|---|
| `POST /conversations` | Signed-in users and support agents; creates an owned conversation |
| `GET /conversations?limit=21&offset=0` | Own conversations only; ordered by `created_at DESC, id DESC` |
| `GET /conversations/{id}` | Owner only; includes the linked ticket or `ticket: null` |
| `GET /conversations/{id}/messages` | Owner only; ordered by message ID |
| `POST /conversations/{id}/messages` | Owner only; trimmed `content` of 1–1000 characters; 409 if converted or busy |
| `POST /conversations/{id}/ticket-draft` | Owner only; returns a validated proposal without creating a ticket |
| `POST /conversations/{id}/tickets` | Owner only; explicit confirmation; 201 on creation, 409 for duplicate, busy or stale requests |
| `POST /tickets` | 410; the former direct creation route is disabled |

Confirmation requires a trimmed `title` (1–160 characters), `description` (1–2000), positive integer `last_message_id` and strict boolean `confirmed: true`. Optional `impact` is `individual`, `team` or `organization`; it is user-declared, not inferred by a model. The edited title and description are classified again. Confirmation must reference the latest message. Transactional locking and a unique conversation-to-ticket constraint protect concurrent requests.

After a lost response, read `GET /conversations/{id}`. A valid linked ticket confirms success. `ticket: null` does not prove the first request has finished; any retry is still protected by the backend. A stale draft requires regeneration and confirmation rather than automatic resubmission of old text.

## Tickets

| Endpoint | Access and behavior |
|---|---|
| `GET /tickets` | Users: own tickets; support: all tickets, including historical records without an owner |
| `GET /tickets/{id}` | Same visibility rules as the list |
| `PATCH /tickets/{id}` | Support only; updates `final_category`, `status` and/or `priority` |
| `GET /tickets/{id}/events` | Anyone who can view the ticket; actor, timestamp, field and old/new values |
| `POST /predict` | Authentication and CSRF required; body `{"text":"..."}` with 1–12000 trimmed characters; returns category and v2 model version |
| `GET /health` | Public database availability check; does not run inference |

List filters are `search` (up to 200 characters; literal case-insensitive match against title, description and UUID), `status`, `category`, `priority`, `assigned_to_me=true` and `unassigned=true`. The last two are support-only and mutually exclusive. Pagination uses `limit` (1–100, default 20) and nonnegative `offset`; order is `created_at DESC, id DESC`. New inserts can shift offset pages.

Access to another user's resources returns 404. Support access to tickets does not grant access to other users' AI conversations. Categories are `Access`, `Administrative rights`, `HR Support`, `Hardware`, `Internal Project`, `Miscellaneous`, `Purchase` and `Storage`. Priorities are `low`, `normal`, `high` and `urgent`; existing tickets receive `normal` during migration. Only support can change priority.

## Ticket collaboration and concurrency

The ticket thread is separate from the AI conversation. Migration 005 adds assignment, optimistic versions, messages and workflow timestamps. `updated_at` tracks metadata/status changes; ordinary replies and internal notes do not change it. Unknown historical timestamps remain unknown. `first_resolved_at` comes from an existing resolution audit event or the first new resolution and is preserved after reopening.

| Endpoint | Rules |
|---|---|
| `GET /support/agents` | Support only; returns support account IDs and emails |
| `GET /tickets/{id}/messages?limit=50&after_id={uuid}` | Owner/support; ordered by `created_at ASC, id ASC`; limit 1–100; cursor must identify a visible message in this ticket |
| `POST /tickets/{id}/messages` | Owner/support; trimmed `content` of 1–4000 characters and UUID `request_id`; `visibility` defaults to `public`; `internal` is support-only |
| `POST /tickets/{id}/claim` | Support; requires `expected_version`; ticket must be unassigned |
| `PUT /tickets/{id}/assignment` | Support; requires `expected_version` and a support `assignee_id`, or `null` to unassign |
| `POST /tickets/{id}/reopen` | Owner/support; requires trimmed `reason` of 1–4000 characters, `expected_version` and UUID `request_id`; only `resolved → open` |

Ticket creation, list and detail responses include `version`. Metadata, status and assignment changes increment it. A stale `expected_version` returns 409 without a partial save. Status and priority changes require a version; category-only updates may omit it, although the frontend always supplies it. Unchanged saves create no audit event.

Support may move `open → in_progress/resolved` or `in_progress → open/resolved`. Resolving through `PATCH` also requires `resolution_message` (1–4000 trimmed characters) and UUID `request_id`; the message is public. Reopening requires the dedicated route and a reason. Ordinary replies, including replies to resolved tickets, never change status. A converted AI conversation remains closed after ticket reopening.

Message `request_id` is unique per ticket and author. Repeating the same content, visibility and message kind returns the existing message; reusing the ID with different values returns 409. Reopen requests use the same deduplication rule. Retrying resolution with an old version can return 409: reload the ticket to inspect the result. Concurrent claims or transitions using the same version have one successful writer.

Internal notes are filtered in SQL before user pagination. A user cursor pointing to an internal note returns 404. Notes are absent from the public audit and do not change the ticket version or public timestamps. Message IDs are UUIDs, and no public note counter is exposed.

## Notifications and support dashboard

| Endpoint | Rules |
|---|---|
| `GET /support/dashboard?days=30` | Support only; `days` between 1 and 365 |
| `GET /notifications?limit=20&offset=0` | Own notifications for accessible tickets; newest first by timestamp/ID; limit 1–50 |
| `GET /notifications/unread-count` | Own unread count for accessible tickets |
| `PATCH /notifications/{id}/read` | Marks an accessible notification belonging to the recipient as read; otherwise 404 |

Notifications persist and deduplicate within the source action's transaction. Public replies notify the owner and assigned agent, excluding the actor; an owner's reply on an unassigned ticket also notifies the support team. Internal notes do not notify. Assignment notifies the owner and new assignee, excluding the actor. Support status changes notify the owner; reopening notifies reply recipients of both the reply and status change. The UI polls every 30 seconds; there is no email delivery.

The dashboard selects tickets whose `created_at` falls in the rolling interval `[now - days, now]`. Status, final-category, priority and unassigned counts describe that cohort, rather than the entire backlog. Timing metrics are arithmetic means in seconds:

- First reply: earliest public support message of kind `reply` or `resolution`, minus ticket creation. Internal notes and reopening reasons are excluded.
- First resolution: `first_resolved_at` minus ticket creation, including tickets subsequently reopened.
- Missing reply/resolution timestamps are excluded from the corresponding average and reported as separate counts. An average with no eligible observations is `null`.

These are descriptive timings, not SLA measurements. Reply/resolution events can occur after the cohort's creation interval.

## Explicit category review and ML export

| Endpoint | Rules |
|---|---|
| `POST /tickets/{id}/category-review` | Support only; `verified_category`, UUID `request_id`, optional `reason` of up to 1000 trimmed characters |
| `GET /tickets/{id}/category-review` | Support only; returns the active review or `review: null` |
| `GET /support/category-review-export?limit=5000` | Support only; CSV of active, explicitly reviewed examples; limit 1–10000 |

Review records retain the reviewer, timestamp, ticket model version and SHA-256 hash of the exact classification text (`title + "\n" + description`). Changing `final_category` alone does not approve an example. A new review invalidates earlier active reviews for that ticket. A database trigger invalidates active reviews if title, description or final category changes; old records remain for provenance. An identical retry returns the original record, even if it has since been invalidated; reusing the request ID with a different label or reason returns 409.

The CSV columns are `ticket_id`, `text`, `label`, `text_sha256`, `model_version`, `reviewer_id` and `reviewed_at`. It does not include separate AI conversation, reply, internal-note, email, password or token fields. Ticket text can still contain personal information. Text whose first non-whitespace character is `=`, `+`, `-` or `@` is prefixed with an apostrophe for spreadsheet safety; the hash refers to the original text. Keep exports outside Git and inspect and anonymize them before reuse. Category review is not a privacy review.

Backend and browser tests substitute inference while exercising real database behavior; the application server has no mock-inference switch. Recorded test and real-model results are in the [verification record](IMPLEMENTATION_PLAN.md).
