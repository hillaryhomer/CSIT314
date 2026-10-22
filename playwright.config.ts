import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/browser',
  fullyParallel: false,
  workers: 1,
  timeout: 45_000,
  use: { baseURL: 'http://127.0.0.1:4174', browserName: 'chromium', trace: 'retain-on-failure' },
  webServer: {
    command: 'node tests/browser-server.mjs',
    url: 'http://127.0.0.1:4174/api/health',
    reuseExistingServer: false,
    timeout: 30_000,
  },
});
