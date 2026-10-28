import { test, expect } from "@playwright/test";

/**
 * Level 1 Systematic Literature Review Browser Acceptance Test.
 * 
 * Contract with D04:
 * Expects backend/app/testing/serve.py to run on 127.0.0.1:8000
 * Expects frontend preview on 127.0.0.1:4173
 */
test.describe("Level 1 Systematic Review Acceptance", () => {
  test("verifies backend readiness and review workbench accessibility", async ({ page, request }) => {
    // 1. Verify backend health ready endpoint
    const healthRes = await request.get("http://127.0.0.1:8000/health/ready", { timeout: 3000 });
    expect(healthRes.ok()).toBeTruthy();
    const healthJson = await healthRes.json();
    expect(healthJson.status).toBe("ready");

    // 2. Navigate to review queue
    await page.goto("/review-queue");
    await expect(page.locator("h1")).toContainText(/Review/i);

    // 3. Verify screening filter buttons exist
    const allFilter = page.getByRole("button", { name: /all/i });
    await expect(allFilter).toBeVisible();
  });
});
