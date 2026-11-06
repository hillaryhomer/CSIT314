import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/browser', testMatch: 'member3.spec.ts', outputDir: 'test-results/member3', workers: 1, timeout: 45_000,
  use: { baseURL: 'http://127.0.0.1:4176', browserName: 'chromium', trace: 'retain-on-failure' },
  globalSetup: './tests/browser-setup.ts',
});
