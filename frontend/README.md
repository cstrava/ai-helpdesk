# AI Helpdesk frontend

React 19, TypeScript, and Vite. Start with the [project README](../README.md) for architecture, application setup, and workflows.

For frontend development, run from this directory after setting up the API:

```bash
npm ci
npm run dev
```

Vite listens on `127.0.0.1:5173` and proxies `/api` to `http://127.0.0.1:8000`. Set `API_PROXY_TARGET` to use another API address. Stop the Compose frontend first if it occupies port 5173.

See [development and test instructions](../docs/OPERATIONS.md) for Python dependencies, the isolated PostgreSQL test database, and Playwright commands. Browser tests use ports 8001 and 5174.
