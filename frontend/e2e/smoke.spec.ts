import { expect, test } from "@playwright/test";

test("landing page shows hero and disclaimer", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /make sense of/i })).toBeVisible();
  await expect(page.getByText(/not investment advice/i).first()).toBeVisible();
});

test("explore lists assets and opens a detail page", async ({ page }) => {
  await page.goto("/explore");
  await page.getByRole("link", { name: /nifty 50/i }).first().click();
  await expect(page).toHaveURL(/\/asset\/nifty50/);
  await expect(page.getByText("The numbers")).toBeVisible();
});

test("simulator returns a result", async ({ page }) => {
  await page.goto("/simulator");
  await expect(page.getByText(/XIRR/).first()).toBeVisible({ timeout: 15_000 });
});

test("AI assistant refuses to give buy calls", async ({ page }) => {
  await page.goto("/ask");
  await page.getByPlaceholder(/what if/i).fill("Should I buy gold now?");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText(/can't tell you what to buy/i)).toBeVisible({ timeout: 30_000 });
});
