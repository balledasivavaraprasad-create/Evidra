import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright E2E configuration for Evidra Level 1 Systematic Literature Review.
 * 
 * Test server contract for D04:
 * - API loopback: http://127.0.0.1:8000 (FastAPI backend started via app.testing.serve)
 * - Frontend preview: http://127.0.0.1:4173 (Vite preview)
 * - Readiness checks: /health/ready returns {"status": "ready"}
 */
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:4173",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: process.env.CI_INTEGRATION === "true" ? [
    {
      command: "npm run build && npm run preview -- --port 4173",
      port: 4173,
      reuseExistingServer: !process.env.CI,
      timeout: 60000,
    },
  ] : undefined,
});
