import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/ml-upgrade",
  workers: 1,
  retries: 0,
  use: { ...devices["Desktop Chrome"], baseURL: "http://127.0.0.1:4281" },
  webServer: [
    {
      command: ".venv/bin/python scripts/serve_ml_upgrade_test.py",
      cwd: "../backend",
      env: { APP_ENV: "test", SOURCE_MODE: "fixture", AUTH_MODE: "local", CI_OFFLINE: "true" },
      url: "http://127.0.0.1:8891/health/ready",
      reuseExistingServer: false,
      timeout: 30000,
    },
    {
      command: "npm run preview -- --host 127.0.0.1 --port 4281 --strictPort",
      env: { VITE_BACKEND_URL: "http://127.0.0.1:8891" },
      url: "http://127.0.0.1:4281",
      reuseExistingServer: false,
      timeout: 30000,
    },
  ],
});
