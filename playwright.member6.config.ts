import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests/browser', testMatch: 'member6.spec.ts', outputDir: 'test-results/member6', workers: 1, timeout: 60_000,
  use: { baseURL: 'http://127.0.0.1:4179', browserName: 'chromium', trace: 'retain-on-failure' },
  globalSetup: './tests/browser-setup.ts',
});
