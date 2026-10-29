import { test, expect } from "@playwright/test";

test("ML decisions persist through reload and exclusions require evidence", async ({ page }) => {
  await page.goto("/reviews/ws-synth-001/ml-ranking");
  await expect(page.getByTestId("ml-review-container")).toBeVisible();
  await expect(page.getByTestId("decision-include-btn")).toBeVisible();
  await expect(page.getByRole("button", { name: "Refresh Ranking" })).toBeVisible();
  await page.getByTestId("decision-include-btn").click();
  await expect(page.getByText("Saved include decision.", { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.locator("[data-testid^='ml-record-']").first()).toContainText(/Decision:\s*include/);
  await page.getByTestId("decision-exclude-btn").click();
  await expect(page.getByText(/Enter an evidence-based exclusion reason/)).toBeVisible();
  await page.getByLabel("Decision reason / supporting evidence (required for exclusion)").fill(
    "Browser fixture: reviewer verified that this record does not meet the saved protocol.");
  await page.getByTestId("decision-exclude-btn").click();
  await expect(page.getByText("Saved exclude decision.", { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.locator("[data-testid^='ml-record-']").first()).toContainText(/Decision:\s*exclude/);
  await expect(page.getByText(/not an eligibility probability/)).toBeVisible();
});
