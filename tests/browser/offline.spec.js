// Offline release tests. They build the packaged layout, open it from a local
// file with the network off, and compare booleans so no secret is printed.
// Set DECK_SITE_URL to run the same checks against a hosted copy.
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { test, expect } from '@playwright/test';

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, '../..');
const hosted = process.env.DECK_SITE_URL || '';
let outDir;
let pageUrl;

test.beforeAll(() => {
  if (hosted) {
    pageUrl = hosted;
    return;
  }
  outDir = fs.mkdtempSync(path.join(os.tmpdir(), 'passphrase-deck-release-'));
  execFileSync('python3', [path.join(repo, 'scripts/package_release.py'), '--out', outDir], { stdio: 'pipe' });
  pageUrl = pathToFileURL(path.join(outDir, 'site', 'index.html')).href;
});

test.afterAll(() => {
  if (outDir) fs.rmSync(outDir, { recursive: true, force: true });
});

async function reveal(page) {
  await page.locator('#readable-reveal').click();
  await page.locator('#compact-reveal').click();
  const readable = await page.locator('#readable-value').textContent();
  const compact = await page.locator('#compact-value').textContent();
  await page.locator('#readable-reveal').click();
  await page.locator('#compact-reveal').click();
  return { readable, compact };
}

test('the packaged copy deals with the network off', async ({ browser }) => {
  const context = await browser.newContext({ offline: true });
  const page = await context.newPage();
  const outside = [];
  const problems = [];
  page.on('request', (r) => { if (!/^(file|data|blob):/.test(r.url()) && !hosted) outside.push(r.url()); });
  page.on('pageerror', (e) => problems.push('pageerror'));
  page.on('console', (m) => { if (m.type() === 'error') problems.push('console'); });
  await page.goto(pageUrl);
  await expect(page.locator('#deal')).toBeEnabled();
  const first = await reveal(page);
  expect(first.compact === first.readable.replaceAll(' ', '')).toBe(true);
  expect(/^[a-z-]+([.,#$_!?] [a-z-]+)+\d+$/.test(first.readable)).toBe(true);
  expect(first.readable.length <= 32 && first.compact.length >= 12).toBe(true);
  await page.locator('#deal').click();
  const second = await reveal(page);
  expect(second.readable === first.readable).toBe(false);
  expect(outside).toEqual([]);
  expect(problems).toEqual([]);
  await context.close();
});

test('copy works or fails clearly when the browser blocks the clipboard', async ({ browser }) => {
  const context = await browser.newContext({ offline: true });
  await context.addInitScript(() => {
    Object.defineProperty(navigator, 'clipboard', { value: undefined, configurable: true });
  });
  const page = await context.newPage();
  await page.goto(pageUrl);
  await expect(page.locator('#deal')).toBeEnabled();
  await page.locator('#readable-copy').click();
  await expect(page.locator('#status')).toContainText('Copy failed');
  // The manual path stays usable: reveal and select the text.
  await page.locator('#readable-reveal').click();
  await expect(page.locator('#readable-value')).not.toHaveText('Hidden');
  await context.close();
});

test('generation and copy make no request after load', async ({ browser }) => {
  const context = await browser.newContext({ offline: true });
  await context.grantPermissions(['clipboard-read', 'clipboard-write'], hosted ? { origin: new URL(hosted).origin } : undefined).catch(() => {});
  const page = await context.newPage();
  await page.goto(pageUrl);
  await expect(page.locator('#deal')).toBeEnabled();
  const late = [];
  page.on('request', (r) => late.push(r.url()));
  await page.locator('#deal').click();
  await reveal(page);
  await page.locator('#readable-copy').click();
  await page.locator('#compact-copy').click();
  await page.waitForTimeout(300);
  expect(late).toEqual([]);
  await context.close();
});

test('the packaged page has a strict policy and no outside origin', async ({ browser }) => {
  const context = await browser.newContext({ offline: true });
  const page = await context.newPage();
  await page.goto(pageUrl);
  const csp = await page.locator('meta[http-equiv="Content-Security-Policy"]').getAttribute('content');
  expect(csp).toContain("default-src 'none'");
  expect(csp).not.toContain('connect-src');
  expect(/https?:|unsafe-/.test(csp)).toBe(false);
  const refs = await page.evaluate(() =>
    [...document.querySelectorAll('script[src], link[href]')].map((e) => e.getAttribute('src') || e.getAttribute('href')));
  expect(refs.length).toBe(3);
  expect(refs.every((r) => !/^([a-z]+:)?\/\//i.test(r))).toBe(true);
  expect(await page.locator('script:not([src])').count()).toBe(0);
  await context.close();
});

test('the packaged layout refuses a corrupt word list', async ({ browser }) => {
  test.skip(Boolean(hosted), 'needs a local copy');
  const copy = fs.mkdtempSync(path.join(os.tmpdir(), 'passphrase-deck-corrupt-'));
  try {
    const site = path.join(outDir, 'site');
    for (const name of fs.readdirSync(site)) {
      let data = fs.readFileSync(path.join(site, name), 'utf8');
      if (name.startsWith('wordlist.')) data = data.replace('abacus', 'abacuz');
      fs.writeFileSync(path.join(copy, name), data);
    }
    const context = await browser.newContext({ offline: true });
    const page = await context.newPage();
    await page.goto(pathToFileURL(path.join(copy, 'index.html')).href);
    await expect(page.getByRole('alert')).toContainText('failed verification');
    await expect(page.locator('#deal')).toBeDisabled();
    await context.close();
  } finally {
    fs.rmSync(copy, { recursive: true, force: true });
  }
});
