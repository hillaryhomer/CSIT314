import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/browser', testMatch: 'member4.spec.ts', outputDir: 'test-results/member4', workers: 1, timeout: 60_000,
  use: { baseURL: 'http://127.0.0.1:4177', browserName: 'chromium', trace: 'retain-on-failure' },
  globalSetup: './tests/browser-setup.ts',
});
