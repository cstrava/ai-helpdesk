# Local operations, migrations and recovery

These commands target the Compose configuration in this checkout. Run them from the repository root unless a section says otherwise. The default application database is `ai_helpdesk`; tests use a separate `ai_helpdesk_test` database.

## Configuration and startup

Docker Engine and Compose v2 are required. The existing Compose configuration reserves an NVIDIA GPU for Ollama and requires an NVIDIA driver and NVIDIA Container Toolkit. The API image runs XLM-R on CPU. Docker builds and the initial Qwen download require network access; runtime XLM-R loading uses local files only.

Provide the trained model artifacts before startup:

```text
ml/models/xlm_roberta_helpdesk_v2/model/
  config.json
  model.safetensors
  tokenizer.json
  tokenizer_config.json
```

The directory is mounted read-only. Model weights and datasets are not included in Git, so a checkout alone cannot run real inference. The application neither trains nor downloads XLM-R weights at startup.

Create `.env` only if it does not already exist:

```bash
if [ ! -e .env ]; then cp .env.example .env; fi
```

Set `POSTGRES_PASSWORD` locally before using Compose. Keep an existing `.env` file. `POSTGRES_PASSWORD` must match an existing database volume: changing the variable does not update the stored PostgreSQL password. `APP_ORIGIN` must match the browser origin exactly; `localhost` and `127.0.0.1` differ. Use `COOKIE_SECURE=false` for local HTTP and `true` behind HTTPS.

For a first installation, start Ollama and download the default chat model before starting the API:

```bash
docker compose up -d ollama
docker compose exec ollama ollama pull qwen3:4b-instruct
```

If you change `CHAT_MODEL`, download that model instead.

```bash
docker compose up -d --build
docker compose ps
docker compose logs --tail=100 api frontend
docker compose exec api python -m backend.app.manage create-support --email support@example.com
```

Default endpoints are the UI at `http://127.0.0.1:5173`, OpenAPI at `http://127.0.0.1:8000/docs`, and PostgreSQL at `127.0.0.1:5434`. Inside Compose, the database is `db:5432` and Ollama is `http://ollama:11434`.

| Setting | Default or requirement |
|---|---|
| `POSTGRES_PASSWORD` | Required in `.env`; no application default |
| `APP_ORIGIN` | `http://127.0.0.1:5173` |
| `COOKIE_SECURE` | `false`; set `true` for HTTPS |
| `CHAT_MODEL` | `qwen3:4b-instruct` |
| `OLLAMA_URL` | `http://ollama:11434` in Compose; `http://localhost:11434` for a local API |

Compose does not publish Ollama's port to the host. A local API needs a separately reachable Ollama instance or an explicit local port mapping.

The last command prompts for a password without echoing it and creates a new support account; it does not promote an existing account. Public registration creates only users. Startup does not create accounts or demonstration data. Use separate synthetic accounts for demonstrations and screenshots.

The API waits for PostgreSQL and Ollama health checks and runs migrations before starting Uvicorn. XLM-R loads before the API accepts requests. Ollama's health check confirms service availability, not that the configured Qwen model has been downloaded. API health checks query the database, not model inference. A failed health check alone does not restart a running container; `restart: unless-stopped` applies when a container exits.

`docker compose stop` preserves data. Do not use `docker compose down -v` for routine shutdown: it deletes the named database and Ollama volumes.

## Before an upgrade

1. Stop application writes during a maintenance window, for example with `docker compose stop frontend api`. Keep the database running.
2. Back up to a private directory outside Git. Use a new filename for every backup. This example records the UTC time to avoid routinely overwriting the previous copy:

```bash
mkdir -p "$HOME/backups/ai-helpdesk"
chmod 700 "$HOME/backups/ai-helpdesk"
backup_path="$HOME/backups/ai-helpdesk/before-upgrade-$(date -u +%Y%m%dT%H%M%SZ).dump"
(umask 077; docker compose exec -T db pg_dump -U helpdesk -d ai_helpdesk -Fc > "$backup_path")
sha256sum "$backup_path"
```

Keep the shell variable for the restore check below, or replace it with the actual backup path. The dump contains private data. Do not publish it or commit it to Git. Back up local configuration separately through a secure mechanism without printing secrets in logs.

3. Restore into a separate PostgreSQL instance with no application volumes or network. Choose a fresh container name if the example name already exists:

```bash
docker run -d --name ai-helpdesk-restore-check --network none \
  -e POSTGRES_HOST_AUTH_METHOD=trust -e POSTGRES_DB=restore_check postgres:17
docker exec ai-helpdesk-restore-check pg_isready -U postgres -d restore_check
```

Repeat `pg_isready` until it reports that PostgreSQL accepts connections, then restore:

```bash
docker exec -i ai-helpdesk-restore-check pg_restore -U postgres -d restore_check \
  --no-owner --no-privileges --exit-on-error < "$backup_path"
docker exec ai-helpdesk-restore-check psql -U postgres -d restore_check -c '\dt'
```

Compare schema, row counts, content and sequence values against the source. A restore without errors does not by itself prove data equivalence. Stop the check container after inspection with `docker stop ai-helpdesk-restore-check`. Do not point restore commands at the existing application database. Actual recovery requires restoring to a new volume, verifying it and explicitly switching the application to it; startup does not restore backups automatically.

4. Apply the upgrade after verifying the backup. Normal Compose startup runs migrations; the explicit alternative is:

```bash
docker compose build api
docker compose run --rm --no-deps api python -m backend.app.manage migrate
docker compose up -d --build
```

The database must be running for the migration command. Migrations are transactional and serialized by a PostgreSQL advisory lock. The runner records applied filenames in `schema_migrations`. It validates manually applied legacy migrations 001–003 against a temporary reference schema before adopting them; this requires permission to create a schema. Incompatible or partial legacy schemas fail with rollback. Already recorded migrations are skipped rather than revalidated.

Migration 004 adds authentication and ownership without assigning historical records to a user. Migration 005 adds collaboration; 006 adds impact, dashboard indexes and notifications; 007 adds category reviews and invalidation on title, description or final-category changes. Historical resolution timestamps are recovered only from existing audit evidence. Do not edit already applied SQL or delete migration records to force adoption.

ML CSV exports include ticket text and provenance. Keep them outside Git and public demonstration material; inspect and anonymize their contents before reuse. Label approval does not establish that text is free of personal information.

## Local development

Use Python 3.13 and Node.js 24, matching CI. The frontend can use the existing Compose API:

```bash
docker compose stop frontend
cd frontend
npm ci
npm run dev
```

Vite binds to `127.0.0.1:5173` and proxies `/api` to `http://127.0.0.1:8000`. `API_PROXY_TARGET` overrides the proxy target. Stop only the Docker frontend to free port 5173.

For a local API, provide PostgreSQL, reachable Ollama and the model artifacts above. From the repository root:

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install torch==2.11.0+cpu --index-url https://download.pytorch.org/whl/cpu
.venv/bin/python -m pip install -r backend/requirements.runtime.txt -c backend/requirements.lock.txt
.venv/bin/python -m backend.app.manage migrate
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

The API loads the root `.env` file. Its host-side database defaults are `127.0.0.1:5434`, database `ai_helpdesk`, user `helpdesk`; `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB` and `POSTGRES_USER` override them. Stop the Docker API before binding local port 8000. Running migrations changes the configured target database; follow the backup procedure before upgrading important data.

## Testing

Use Python 3.13 and Node.js 24, matching CI. Create a test environment if one is not already available:

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.test.txt
docker run -d --name ai-helpdesk-tests -p 127.0.0.1:55434:5432 \
  -e POSTGRES_USER=helpdesk -e POSTGRES_DB=ai_helpdesk_test \
  -e POSTGRES_HOST_AUTH_METHOD=trust postgres:17
docker exec ai-helpdesk-tests pg_isready -U helpdesk -d ai_helpdesk_test
```

Wait until PostgreSQL accepts connections. This test-only instance uses trust authentication on a loopback-published port and has no application volumes. `test-only` below is a fixture value, not an application password.

```bash
POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=55434 POSTGRES_USER=helpdesk POSTGRES_PASSWORD=test-only \
  .venv/bin/python -m pytest backend/tests -q --tb=short
cd frontend
npm ci
npm run lint
npm test
npm run build
npx playwright install chromium
E2E_PYTHON=../.venv/bin/python POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=55434 POSTGRES_USER=helpdesk \
  npm run test:e2e
```

Lint and build each include TypeScript checking. On Linux, Playwright may require system browser dependencies; CI installs Chromium with `npx playwright install --with-deps chromium`. Browser tests start dedicated servers on 8001 and 5174 and refuse to reuse existing servers. Database fixtures create and remove temporary schemas in `ai_helpdesk_test`. They must never use the application database. Inference is substituted in automated tests; real-model checks are recorded separately in the [verification record](IMPLEMENTATION_PLAN.md).

## Troubleshooting

| Symptom | Check |
|---|---|
| Compose rejects `POSTGRES_PASSWORD` | Set it in local `.env`; retain the password for an existing volume |
| API build/start reports a missing model directory | Restore the required local v2 artifacts at the read-only bind path described in the README |
| Ollama is healthy but chat fails | Check `CHAT_MODEL` and download that model using `docker compose exec ollama ollama pull qwen3:4b-instruct` for the default configuration |
| GPU reservation fails | Check the NVIDIA driver and NVIDIA Container Toolkit required by the existing Compose configuration |
| Login or writes return 403 | Use the exact `APP_ORIGIN`, cookie and CSRF token; check `COOKIE_SECURE` for local HTTP |
| Login/register returns 429 | Wait for the ten-minute limit window; local proxy clients share a bucket |
| Migration fails | Inspect `docker compose logs --tail=100 api`; verify the target schema and backup before making changes |
| Tests cannot connect to PostgreSQL | Check the isolated database readiness and `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER` and `POSTGRES_PASSWORD` values |
| Browser tests cannot start | Free test ports 8001/5174 and ensure Chromium is installed |

Do not reset volumes or alter migration history as a troubleshooting shortcut. Application and API access rules are documented in [API.md](API.md).
