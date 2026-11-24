import os from 'node:os';
import path from 'node:path';
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: '.',
  outputDir: path.join(os.tmpdir(), 'passphrase-deck-playwright'),
  testMatch: '*.spec.js',
  reporter: 'line',
  use: { baseURL: 'http://127.0.0.1:4173', browserName: 'chromium' },
  webServer: {
    command: 'node server.mjs',
    url: 'http://127.0.0.1:4173/',
    reuseExistingServer: false,
  },
});
