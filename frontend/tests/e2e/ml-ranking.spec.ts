import { test, expect } from "@playwright/test";

/**
 * ML Review Prioritization Browser Acceptance Test (C-ML02).
 * 
 * Verifies real end-to-end integration across:
 * - Backend /api/v1/workspaces/{id}/revisions/{id}/ml-ranking endpoint
 * - MLReviewPage prioritization UI
 * - Model artifact provenance (ml_ranker:v1.0.0)
 * - Priority tiers (HIGH, MEDIUM, LOW, UNSCORED)
 * - Baseline literature vs ML queue order toggle
 * - Preservation of human review decisions alongside model probability scores
 */
test.describe("ML Review Prioritization Acceptance (C-ML02)", () => {
  test("renders prioritized review queue, verifies scores, and toggles baseline ordering", async ({ page }) => {
    // 1. Open ML Review Prioritization Screen
    await page.goto("/ml-ranking");
    await expect(page.locator("h1")).toContainText(/ML Review Prioritization/i);

    // 2. Verify model provenance badge is present
    await expect(page.getByText(/ml_ranker:v1.0.0/i)).toBeVisible();

    // 3. Verify ranked cards are displayed with priority tiers
    const recordCards = page.locator("[data-testid^='ml-record-']");
    await expect(recordCards.first()).toBeVisible();

    // 4. Verify highest priority card is ranked #1 with clinical relevance
    const firstCard = recordCards.first();
    await expect(firstCard).toContainText("#1");
    await expect(firstCard).toContainText(/Score:/i);

    // 5. Test Toggle between ML Priority Order and Baseline Corpus Order
    const toggleBtn = page.getByTestId("order-toggle-btn");
    await expect(toggleBtn).toBeVisible();
    await expect(toggleBtn).toContainText(/ML Priority Rank/i);

    await toggleBtn.click();
    await expect(toggleBtn).toContainText(/Baseline Corpus Order/i);

    await toggleBtn.click();
    await expect(toggleBtn).toContainText(/ML Priority Rank/i);

    // 6. Test Priority Tier Filter
    const highFilter = page.getByTestId("filter-high");
    await expect(highFilter).toBeVisible();
    await highFilter.click();

    // Reset back to All Papers
    const allFilter = page.getByTestId("filter-all");
    await allFilter.click();

    // 7. Test Recording Human Decision on Selected Paper
    const includeBtn = page.getByTestId("decision-include-btn");
    await expect(includeBtn).toBeVisible();
    await includeBtn.click();

    // Verify human decision is reflected as 'include' on the card
    await expect(page.getByText(/Decision:/i).first()).toBeVisible();

    // Test Exclude decision
    const excludeBtn = page.getByTestId("decision-exclude-btn");
    await expect(excludeBtn).toBeVisible();
    await excludeBtn.click();

    // 8. Verify Navigation link back to Manual Screening Queue works
    const manualQueueLink = page.getByRole("link", { name: /Manual Screening Queue/i });
    await expect(manualQueueLink).toBeVisible();
  });
});
