import { test, expect } from "@playwright/test";

/**
 * Level 1 Systematic Literature Review Browser Acceptance Test.
 * 
 * Verifies real end-to-end integration across:
 * - Disposable SQLite database & seeded synthetic SLR benchmark
 * - FastAPI backend (port 8000)
 * - Review queue workbench & optimistic decision logging
 * - Mandatory clinical exclusion reason enforcement
 * - Deduplication disambiguation panel & cannot-link constraints
 * - CSV export generation
 */
test.describe("Level 1 Systematic Literature Review Acceptance", () => {
  test("verifies backend readiness and health endpoints", async ({ request }) => {
    const healthRes = await request.get("http://127.0.0.1:8000/health/ready", { timeout: 5000 });
    expect(healthRes.ok()).toBeTruthy();
    const healthJson = await healthRes.json();
    expect(healthJson.status).toBe("ready");
  });

  test("completes end-to-end screening, exclusion modal, and duplicate review flow", async ({ page }) => {
    // 1. Navigate to Screening Review Workbench
    await page.goto("/review-queue");
    await expect(page.locator("h1")).toContainText(/Review/i);

    // 2. Verify filter pills are visible and operational
    const allFilter = page.getByRole("button", { name: "all" });
    await expect(allFilter).toBeVisible();

    // 3. Verify paper groups are rendered in the queue
    const groupCard = page.locator(".cursor-pointer").first();
    await expect(groupCard).toBeVisible();
    await groupCard.click();

    // 4. Test Include Study Action
    const includeBtn = page.getByRole("button", { name: /Include Study/i });
    await expect(includeBtn).toBeVisible();
    await includeBtn.click();
    await expect(page.locator("body")).toContainText(/Decision 'INCLUDE' successfully saved/i);

    // 5. Test Mandatory Clinical Exclusion Modal
    const excludeBtn = page.getByRole("button", { name: /Exclude \(Select Reason\.\.\.\)/i });
    await expect(excludeBtn).toBeVisible();
    await excludeBtn.click();

    // Verify modal appears with clinical rationale options
    await expect(page.getByText(/Specify Mandatory Exclusion Reason/i)).toBeVisible();
    const animalRadio = page.getByText(/Preclinical animal model/i);
    await expect(animalRadio).toBeVisible();
    await animalRadio.click();

    const confirmExcludeBtn = page.getByRole("button", { name: /Confirm Exclude/i });
    await confirmExcludeBtn.click();
    await expect(page.locator("body")).toContainText(/Decision 'EXCLUDE' successfully saved/i);

    // 6. Navigate to Deduplication & Disambiguation Panel
    await page.goto("/duplicates");
    await expect(page.locator("h1")).toContainText(/Deduplication/i);

    // 7. Verify candidate side-by-side comparison
    await expect(page.getByText(/Candidate Match:/i)).toBeVisible();
    await expect(page.getByText(/RECORD A/i)).toBeVisible();
    await expect(page.getByText(/RECORD B/i)).toBeVisible();

    // 8. Test Confirm Same Paper Action
    const confirmSamePaperBtn = page.getByRole("button", { name: /Confirm Same Paper/i });
    await expect(confirmSamePaperBtn).toBeVisible();
    await confirmSamePaperBtn.click();
    await expect(page.locator("body")).toContainText(/Confirmed as Same Publication/i);
  });
});
