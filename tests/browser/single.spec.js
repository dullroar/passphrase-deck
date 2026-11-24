// Single-file release tests. They build passphrase.html, open it from a local
// file and from a local server with the network blocked, and compare booleans
// so no secret is printed.
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { test, expect } from '@playwright/test';

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, '../..');
let outDir;
let filePath;
let server;
let serverUrl;

// Set DECK_SITE_URL to run the "server" tests against a hosted copy. Select
// them with: playwright test single.spec.js -g "server"
const hosted = process.env.DECK_SITE_URL || '';

test.beforeAll(async () => {
  if (hosted) {
    serverUrl = hosted;
    return;
  }
  outDir = fs.mkdtempSync(path.join(os.tmpdir(), 'passphrase-deck-single-'));
  execFileSync('python3', [path.join(repo, 'scripts/package_release.py'), '--out', outDir], { stdio: 'pipe' });
  filePath = path.join(outDir, 'passphrase.html');
  const body = fs.readFileSync(filePath);
  server = http.createServer((req, res) => {
    if (req.url === '/passphrase.html') {
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-cache' });
      res.end(body);
    } else {
      res.writeHead(404);
      res.end();
    }
  });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  serverUrl = `http://127.0.0.1:${server.address().port}/passphrase.html`;
});

test.afterAll(async () => {
  if (server) await new Promise((resolve) => server.close(resolve));
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

// Open the page with every request except the page itself blocked.
async function open(browser, where) {
  const context = await browser.newContext();
  const url = where === 'file' ? pathToFileURL(filePath).href : serverUrl;
  const blocked = [];
  const problems = [];
  await context.route('**/*', (route) => {
    const target = route.request().url();
    if (target === url) return route.continue();
    blocked.push(target);
    return route.abort();
  });
  const page = await context.newPage();
  page.on('pageerror', () => problems.push('pageerror'));
  page.on('console', (m) => { if (m.type() === 'error') problems.push('console'); });
  await page.goto(url);
  return { context, page, blocked, problems };
}

for (const where of ['file', 'server']) {
  test(`passphrase.html deals from a ${where} with the network blocked`, async ({ browser }) => {
    const { context, page, blocked, problems } = await open(browser, where);
    await expect(page.locator('#deal')).toBeEnabled();
    const first = await reveal(page);
    expect(first.compact === first.readable.replaceAll(' ', '')).toBe(true);
    expect(/^[a-z-]+(_ [a-z-]+)+\d+$/.test(first.readable)).toBe(true);
    expect(first.readable.length <= 32 && first.compact.length >= 12).toBe(true);
    await page.locator('#deal').click();
    const second = await reveal(page);
    expect(second.readable === first.readable).toBe(false);
    expect(blocked).toEqual([]);
    expect(problems).toEqual([]);
    await context.close();
  });
}

test('passphrase.html makes no request after load', async ({ browser }) => {
  const { context, page } = await open(browser, 'file');
  await expect(page.locator('#deal')).toBeEnabled();
  const late = [];
  page.on('request', (r) => late.push(r.url()));
  await page.locator('#deal').click();
  await reveal(page);
  await page.locator('#readable-copy').click();
  await page.waitForTimeout(300);
  expect(late).toEqual([]);
  await context.close();
});

test('copy fails clearly when the browser blocks the clipboard', async ({ browser }) => {
  const context = await browser.newContext({ offline: true });
  await context.addInitScript(() => {
    Object.defineProperty(navigator, 'clipboard', { value: undefined, configurable: true });
  });
  const page = await context.newPage();
  await page.goto(pathToFileURL(filePath).href);
  await expect(page.locator('#deal')).toBeEnabled();
  await page.locator('#readable-copy').click();
  await expect(page.locator('#status')).toContainText('Copy failed');
  await page.locator('#readable-reveal').click();
  await expect(page.locator('#readable-value')).not.toHaveText('Hidden');
  await context.close();
});

test('passphrase.html has a hash policy and loads nothing else', async ({ browser }) => {
  const { context, page } = await open(browser, 'file');
  const csp = await page.locator('meta[http-equiv="Content-Security-Policy"]').getAttribute('content');
  expect(csp).toContain("default-src 'none'");
  expect(/script-src 'sha256-[A-Za-z0-9+/]{43}='; style-src 'sha256-[A-Za-z0-9+/]{43}='/.test(csp)).toBe(true);
  expect(/unsafe-|'self'|https?:|connect-src/.test(csp)).toBe(false);
  expect(await page.locator('script').count()).toBe(1);
  expect(await page.locator('script[src]').count()).toBe(0);
  expect(await page.locator('style').count()).toBe(1);
  expect(await page.locator('link[href]').count()).toBe(0);
  await context.close();
});

for (const where of ['file', 'server']) {
  test(`the policy blocks an injected inline script and style from a ${where}`, async ({ browser }) => {
    const { context, page } = await open(browser, where);
    await expect(page.locator('#deal')).toBeEnabled();
    const result = await page.evaluate(async () => {
      const violations = [];
      document.addEventListener('securitypolicyviolation', (e) => violations.push(e.violatedDirective));
      const script = document.createElement('script');
      script.textContent = 'window.__injected = true;';
      document.body.appendChild(script);
      const style = document.createElement('style');
      style.textContent = 'h1 { color: rgb(1, 2, 3) !important; }';
      document.head.appendChild(style);
      await new Promise((resolve) => setTimeout(resolve, 100));
      return {
        ran: window.__injected === true,
        styled: getComputedStyle(document.querySelector('h1')).color === 'rgb(1, 2, 3)',
        violations,
      };
    });
    expect(result.ran).toBe(false);
    expect(result.styled).toBe(false);
    expect(result.violations.some((v) => v.startsWith('script-src'))).toBe(true);
    expect(result.violations.some((v) => v.startsWith('style-src'))).toBe(true);
    await context.close();
  });
}

test('passphrase.html refuses a corrupt word list', async ({ browser }) => {
  const copy = fs.mkdtempSync(path.join(os.tmpdir(), 'passphrase-deck-single-corrupt-'));
  try {
    const target = path.join(copy, 'passphrase.html');
    // The CSP hash no longer matches, so the browser must block the script.
    // Either way the page must not deal.
    fs.writeFileSync(target, fs.readFileSync(filePath, 'utf8').replace('abacus', 'abacuz'));
    const context = await browser.newContext({ offline: true });
    const page = await context.newPage();
    await page.goto(pathToFileURL(target).href);
    await page.waitForTimeout(300);
    await expect(page.locator('#deal')).toBeDisabled();
    await context.close();
  } finally {
    fs.rmSync(copy, { recursive: true, force: true });
  }
});
