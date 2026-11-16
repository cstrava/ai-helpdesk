# v1.0.0 verification

## Source and integration

Release checks were rerun on 16 November 2026 against `b8e306a99339cd691ff74b32d04c2c8262638c3f`, containing all five implementation stages and the English documentation. [PR #6](https://github.com/cstrava/ai-helpdesk/pull/6) integrates that history into `main` with a merge commit. The earlier stage PRs are retained as historical review records.

Later release-preparation commits change documentation only. The verified application trees are:

| Path | Git object ID |
|---|---|
| `backend/` | `1d7e6cdefd6d0ea082c968ea6d22277c5b4c5022` |
| `frontend/` | `8e136203a9fd4369509b44a7e2a1e51e5a0c8917` |
| `compose.yaml` | `3511139a25323ffd4aafa4d648de7a2ea11cdf43` |
| `ml/src/` | `f105cc6ee5450cfd36d42c8ee85353ea7d2b7fcb` |

These IDs allow comparison with the integrated commit without relying on a similar branch name. The release notes identify the final `main` commit and its CI run. The workflow runs on every push and pull request, including `main`.

## Automated checks rerun locally

A new PostgreSQL 17 container, `ai-helpdesk-v1-tests`, published only on `127.0.0.1:55435`, hosted `ai_helpdesk_test` with temporary test schemas. It used no application volumes. From the repository root:

```bash
POSTGRES_PORT=55435 POSTGRES_PASSWORD=test-only .venv/bin/python -m pytest backend/tests -q --tb=short -p no:cacheprovider
cd frontend
npm ci
npm run typecheck
npm run lint
npm test
npm run build
E2E_PYTHON=../.venv/bin/python POSTGRES_PORT=55435 npm run test:e2e
```

| Check | Result |
|---|---|
| Backend | 57 passed |
| Frontend | 24 passed; confirmed again with the Vitest JSON reporter |
| TypeScript, lint, production build | Passed |
| Playwright | 4 passed: both flows on desktop Chromium and Pixel 7 emulation |
| Clean npm installation | Passed; audit reported zero vulnerabilities at installation time |

The backend suite covers user/support authorization, cross-account isolation, private-note visibility and cursor protection, concurrent confirmation and message deduplication, stale versions, fresh migrations and legacy upgrades with data preservation. Browser tests exercise the complete user/support flow and recovery after a confirmation response is replaced by HTTP 502. These tests use real HTTP and PostgreSQL with simulated inference. The test container was stopped without deleting storage.

The matching [push CI run](https://github.com/cstrava/ai-helpdesk/actions/runs/43844274041) and [PR CI run](https://github.com/cstrava/ai-helpdesk/actions/runs/43844387345) also passed. The final `main` CI run is linked from the release notes after integration.

## Docker and real-model integration

The current API and frontend Dockerfiles built successfully in a separate Compose project, `ai-helpdesk-v1-release`, with a new PostgreSQL volume and database `ai_helpdesk_release`. Nginx was published on `127.0.0.1:5177`, and the API on `127.0.0.1:8005`. The stack used the existing Ollama service for inference and mounted the existing classifier read-only. It did not retrain or replace either model.

Forty HTTP assertions through Nginx covered real Qwen and XLM-R v2 Romanian and English conversations, editable drafts, classification, confirmation, and duplicate-confirmation rejection. Additional checks covered user/support authorization, another user's isolation, support's lack of access to another user's AI conversation, internal-note filtering and private cursor rejection, idempotent note submission, a public reply, claim, stale-version rejection, resolution, reopening, dashboard permissions, notifications, explicit category review and export permissions. The two observed classifier outputs were Hardware and Access; these examples are not an accuracy estimate.

SQL inspection confirmed that the response ticket IDs and synthetic accounts belonged to the isolated release database, with migrations 001–007 recorded. A read-only query of the personal database found none of the release smoke-test accounts. The real-model checks used an HTTP client, not browser automation.

Recreating the isolated database container with the same dedicated volume and restarting the API/frontend preserved the prior session, conversation-to-ticket link and public thread. An explicit second migration run exited successfully. The temporary stack was stopped afterward without deleting its volume; the personal application stack was not upgraded.

Built image IDs:

- API: `sha256:b6b0eb54bffb5b3d9bf95a5da12b3886540f62ec7b3d3319d42e0c7dd1bcc21a`
- Frontend: `sha256:dddd392b1896ac5acf6c68f34f9b2dbd9add544a1879cd0b82a99ce96a3ee7a8`

## Limits

The full ML evaluation was not rerun for this release: its checked-in reports are historical inference results with model/data hashes, described in [ML evaluation](ML_EVALUATION.md). No model was retrained or replaced. Real-model smoke checks validate examples and integration, not general model quality.

Browser coverage remains Chromium desktop and Pixel 7 emulation. Firefox, Safari, physical devices and a complete accessibility audit were not checked. No cloud deployment was performed. Local setup, backup and migrations are documented in [Operations](OPERATIONS.md).
