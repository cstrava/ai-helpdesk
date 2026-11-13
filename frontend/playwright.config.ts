import { defineConfig, devices } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  use: {
    baseURL: "http://127.0.0.1:5174",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    {
      name: "mobile",
      use: { ...devices["Pixel 7"], defaultBrowserType: "chromium" },
    },
  ],
  webServer: [
    {
      command: `${process.env.E2E_PYTHON || "python3"} ../backend/tests/browser_server.py`,
      url: "http://127.0.0.1:8001/health",
      reuseExistingServer: false,
      env: {
        POSTGRES_PORT: process.env.POSTGRES_PORT || "55434",
        POSTGRES_PASSWORD: "test-only",
        APP_ORIGIN: "http://127.0.0.1:5174",
      },
    },
    {
      command: "npm run dev -- --port 5174",
      url: "http://127.0.0.1:5174",
      reuseExistingServer: false,
      env: { API_PROXY_TARGET: "http://127.0.0.1:8001" },
    },
  ],
});
