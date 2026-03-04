// @ts-check
const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './scripts',
  testMatch: 'e2e-smoke.spec.js',
  timeout: 30000,
  retries: 1,
  use: {
    headless: true,
    ignoreHTTPSErrors: true,
  },
  projects: [
    { name: 'chromium', use: { browserName: 'chromium' } },
  ],
});
