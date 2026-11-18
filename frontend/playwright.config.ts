import { defineConfig } from "@playwright/test";

// Run with the API and web app already running:  npx playwright install chromium && npm run test:e2e
export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  use: { baseURL: process.env.E2E_BASE_URL || "http://localhost:3000", trace: "retain-on-failure" },
});
