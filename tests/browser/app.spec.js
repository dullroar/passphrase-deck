// Browser tests. Assertions compare booleans so a failure never prints a real secret.
import { test, expect } from '@playwright/test';

const SHAPE = /^[a-z-]+([.,#$_!?] [a-z-]+)+\d+$/;

async function ready(page) {
  await page.goto('/');
  await expect(page.locator('#deal')).toBeEnabled();
}

async function readSecrets(page) {
  await page.locator('#readable-reveal').click();
  await page.locator('#compact-reveal').click();
  const readable = await page.locator('#readable-value').textContent();
  const compact = await page.locator('#compact-value').textContent();
  await page.locator('#readable-reveal').click();
  await page.locator('#compact-reveal').click();
  return { readable, compact };
}

test('starts hidden with both formats and one-secret wording', async ({ page }) => {
  await ready(page);
  await expect(page.locator('#readable-value')).toHaveText('Hidden');
  await expect(page.locator('#compact-value')).toHaveText('Hidden');
  await expect(page.getByRole('button', { name: 'Deal another pair' })).toBeVisible();
  await expect(page.getByRole('heading', { name: /one secret, two formats/ })).toBeVisible();
  const { readable, compact } = await readSecrets(page);
  expect(compact === readable.replaceAll(' ', '')).toBe(true);
  expect(SHAPE.test(readable)).toBe(true);
  expect(readable.length <= 32 && compact.length >= 12).toBe(true);
});

test('reveal and hide remove the secret from the DOM', async ({ page }) => {
  await ready(page);
  const reveal = page.locator('#readable-reveal');
  await expect(reveal).toHaveAttribute('aria-pressed', 'false');
  await reveal.click();
  await expect(reveal).toHaveAttribute('aria-pressed', 'true');
  await expect(reveal).toHaveText('Hide readable');
  const secret = await page.locator('#readable-value').textContent();
  expect(secret !== 'Hidden').toBe(true);
  await expect(page.locator('#compact-value')).toHaveText('Hidden');
  await reveal.click();
  await expect(page.locator('#readable-value')).toHaveText('Hidden');
  const html = await page.content();
  expect(html.includes(secret)).toBe(false);
});

test('copy writes the chosen format to the clipboard', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await ready(page);
  const { readable, compact } = await readSecrets(page);
  await page.locator('#compact-copy').click();
  await expect(page.locator('#status')).toContainText('Copied the compact format');
  expect(await page.evaluate(() => navigator.clipboard.readText()) === compact).toBe(true);
  await page.locator('#readable-copy').click();
  await expect(page.locator('#status')).toContainText('Copied the readable format');
  expect(await page.evaluate(() => navigator.clipboard.readText()) === readable).toBe(true);
  const status = await page.locator('#status').textContent();
  expect(status.includes(readable) || status.includes(compact)).toBe(false);
  expect(/clipboard (was )?cleared/i.test(status)).toBe(false);
});

test('copy denial is reported accurately', async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: () => Promise.reject(new DOMException('denied', 'NotAllowedError')) },
    });
  });
  await ready(page);
  await page.locator('#readable-copy').click();
  await expect(page.locator('#status')).toContainText('Copy failed');
  await expect(page.locator('#status')).not.toContainText('Copied');
});

test('deal another pair replaces the secret and hides it again', async ({ page }) => {
  await ready(page);
  const first = await readSecrets(page);
  await page.locator('#readable-reveal').click();
  await page.locator('#deal').click();
  await expect(page.locator('#readable-value')).toHaveText('Hidden');
  await expect(page.locator('#readable-reveal')).toHaveAttribute('aria-pressed', 'false');
  const second = await readSecrets(page);
  expect(first.readable === second.readable).toBe(false);
});

test('keyboard use works for deal, reveal, and copy', async ({ page }) => {
  await ready(page);
  await page.locator('#deal').focus();
  await page.keyboard.press('Enter');
  await page.keyboard.press('Tab');
  await expect(page.locator('#readable-reveal')).toBeFocused();
  await page.keyboard.press('Space');
  await expect(page.locator('#readable-value')).not.toHaveText('Hidden');
  await page.keyboard.press('Space');
  await expect(page.locator('#readable-value')).toHaveText('Hidden');
  await page.keyboard.press('Tab');
  await expect(page.locator('#readable-copy')).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(page.locator('#compact-reveal')).toBeFocused();
});

test('accessibility semantics expose names, states, and live regions', async ({ page }) => {
  await ready(page);
  await expect(page.getByRole('button', { name: 'Reveal readable' })).toHaveAttribute('aria-pressed', 'false');
  await expect(page.getByRole('button', { name: 'Copy compact' })).toBeEnabled();
  await expect(page.getByRole('status')).toHaveCount(1);
  await expect(page.locator('#error')).toHaveAttribute('role', 'alert');
  for (const label of ['Minimum length (1–128)', 'Maximum length (1–128)',
    'Minimum entropy in bits (64–128)', 'Capitalize the first letter of each word']) {
    await expect(page.getByLabel(label)).toBeVisible();
  }
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
  const tree = await page.locator('main').ariaSnapshot();
  expect(tree).toContain('Reveal readable');
  expect(tree).toContain('Hidden');
  await page.getByRole('button', { name: 'Reveal readable' }).click();
  const shown = await page.locator('#readable-value').textContent();
  const after = await page.locator('main').ariaSnapshot();
  expect(after.includes(shown)).toBe(true);
  expect(after).toContain('Hide readable');
});

test('settings expose length, entropy, capitalization, and symbols', async ({ page }) => {
  await ready(page);
  await expect(page.locator('#settings input')).toHaveCount(5);
  await page.getByRole('button', { name: /Restrictive-site preset/ }).click();
  await expect(page.locator('#capitalize')).toBeChecked();
  await expect(page.locator('#symbols')).toHaveValue('.,#$_!?');
  await page.locator('#deal').click();
  const { readable } = await readSecrets(page);
  expect(readable.split(/[.,#$_!?] /).every((w) => /^[A-Z]/.test(w))).toBe(true);
});

test('the symbol set is used, and a single symbol repeats', async ({ page }) => {
  await ready(page);
  await page.getByLabel(/Separator symbols/).fill('%');
  await page.locator('#deal').click();
  const { readable, compact } = await readSecrets(page);
  expect(/^[a-z-]+(% [a-z-]+)+\d+$/.test(readable)).toBe(true);
  expect(compact === readable.replaceAll(' ', '')).toBe(true);
});

test('a bad symbol set stops the deal and shows no passphrase', async ({ page }) => {
  await ready(page);
  const field = page.locator('#symbols');
  await field.fill('%');
  await page.locator('#deal').click();
  const first = await readSecrets(page);
  expect(/^[a-z-]+(% [a-z-]+)+\d+$/.test(first.readable)).toBe(true);
  for (const bad of ['', 'a', '1', '. ', '%%', 'é', '.'.repeat(33)]) {
    await field.fill(bad);
    await expect(page.locator('#symbols-error')).toBeVisible();
    await expect(page.locator('#symbols-error')).not.toContainText('last good');
    await expect(field).toHaveAttribute('aria-invalid', 'true');
    await page.locator('#deal').click();
    await expect(page.locator('#symbols-error')).toBeVisible();
    const state = await page.evaluate(() => document.body.innerText);
    expect(state.includes(first.readable)).toBe(false);
    expect(state.includes(first.compact)).toBe(false);
    await expect(page.locator('#readable-reveal')).toBeDisabled();
    await expect(page.locator('#compact-reveal')).toBeDisabled();
    await expect(page.locator('#readable-value')).toHaveText('Hidden');
  }
  await field.fill('%&');
  await expect(page.locator('#symbols-error')).toBeHidden();
  await page.locator('#deal').click();
  const { readable } = await readSecrets(page);
  expect(/^[a-z-]+([%&] [a-z-]+)+\d+$/.test(readable)).toBe(true);
});

test('a hyphen is an allowed separator symbol', async ({ page }) => {
  await ready(page);
  await page.locator('#symbols').fill('-');
  await expect(page.locator('#symbols-error')).toBeHidden();
  await page.locator('#deal').click();
  const { readable, compact } = await readSecrets(page);
  expect(/^[a-z-]+(- [a-z-]+)+\d+$/.test(readable)).toBe(true);
  expect(compact === readable.replaceAll(' ', '')).toBe(true);
});

test('the reset control restores the default symbols by keyboard', async ({ page }) => {
  await ready(page);
  await page.locator('#symbols').fill('%');
  await page.locator('#symbols-reset').focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('#symbols')).toHaveValue('.,#$_!?');
  await expect(page.locator('#symbols-error')).toBeHidden();
});

test('markup-like symbols show as text', async ({ page }) => {
  await ready(page);
  for (const symbol of ['<', '&', '"', "'", '>']) {
    await page.locator('#symbols').fill(symbol);
    await page.locator('#deal').click();
    const { readable } = await readSecrets(page);
    expect(readable.includes(`${symbol} `)).toBe(true);
    expect(await page.locator('#readable-value > *').count()).toBe(0);
  }
  await page.locator('#symbols').fill('<');
  await expect(page.locator('#symbols-error')).toBeHidden();
});

test('capitalization off by default gives lowercase words', async ({ page }) => {
  await ready(page);
  const { readable } = await readSecrets(page);
  expect(/[A-Z]/.test(readable)).toBe(false);
});

test('an infeasible policy shows a suggestion and no secret', async ({ page }) => {
  await ready(page);
  await page.locator('#maximum').fill('14');
  await page.locator('#deal').click();
  const alert = page.getByRole('alert');
  await expect(alert).toContainText('Try a maximum length');
  await expect(page.locator('#readable-value')).toHaveText('Hidden');
  await expect(page.locator('#readable-reveal')).toBeDisabled();
  await expect(page.locator('#compact-copy')).toBeDisabled();
});

test('invalid input shows an error and keeps the floor', async ({ page }) => {
  await ready(page);
  await page.locator('#entropy').fill('40');
  await page.locator('#deal').click();
  await expect(page.getByRole('alert')).toContainText('entropy from 64 to 128');
  await page.locator('#entropy').fill('64');
  await page.locator('#minimum').fill('30');
  await page.locator('#maximum').fill('20');
  await page.locator('#deal').click();
  await expect(page.getByRole('alert')).toBeVisible();
  await page.locator('#minimum').fill('12');
  await page.locator('#maximum').fill('48');
  await page.locator('#entropy').fill('80');
  await page.locator('#deal').click();
  await expect(page.getByRole('alert')).toBeHidden();
  await expect(page.locator('#readable-reveal')).toBeEnabled();
});

test('layout is side by side on wide screens and stacked on phones', async ({ page }) => {
  await page.setViewportSize({ width: 1200, height: 800 });
  await ready(page);
  const a = await page.locator('#readable-heading').boundingBox();
  const b = await page.locator('#compact-heading').boundingBox();
  expect(Math.abs(a.y - b.y) < 4 && b.x > a.x + 100).toBe(true);
  await page.setViewportSize({ width: 375, height: 800 });
  const c = await page.locator('#readable-heading').boundingBox();
  const d = await page.locator('#compact-heading').boundingBox();
  expect(d.y > c.y + 50 && Math.abs(c.x - d.x) < 4).toBe(true);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
  expect(overflow).toBe(false);
});

test('no network request during deal or copy and no storage of secrets', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  const logs = [];
  page.on('console', (m) => logs.push(m.text()));
  page.on('pageerror', (e) => logs.push(String(e)));
  await ready(page);
  const origin = new URL(page.url()).origin;
  const late = [];
  page.on('request', (r) => late.push(r.url()));
  await page.route('**/*', (route) => route.continue());
  await page.locator('#deal').click();
  await page.locator('#deal').click();
  const { readable, compact } = await readSecrets(page);
  await page.locator('#readable-copy').click();
  await page.locator('#compact-copy').click();
  await page.waitForTimeout(300);
  expect(late.length).toBe(0);

  const state = await page.evaluate(async () => ({
    url: location.href,
    cookie: document.cookie,
    local: JSON.stringify({ ...localStorage }),
    session: JSON.stringify({ ...sessionStorage }),
    caches: await caches.keys(),
    databases: indexedDB.databases ? (await indexedDB.databases()).length : 0,
    title: document.title,
  }));
  const pool = [state.url, state.cookie, state.local, state.session, state.title, ...logs];
  for (const secret of [readable, compact]) {
    expect(pool.some((text) => text.includes(secret))).toBe(false);
  }
  expect(state.local).toBe('{}');
  expect(state.session).toBe('{}');
  expect(state.caches).toEqual([]);
  expect(state.databases).toBe(0);
  expect((await context.cookies()).length).toBe(0);
  expect(state.url).toBe(`${origin}/`);
});

test('every load request is same origin and CSP blocks outside origins', async ({ page }) => {
  const urls = [];
  page.on('request', (r) => urls.push(r.url()));
  await ready(page);
  const origin = new URL(page.url()).origin;
  expect(urls.every((u) => u.startsWith(origin + '/'))).toBe(true);
  const csp = await page.locator('meta[http-equiv="Content-Security-Policy"]').getAttribute('content');
  expect(csp).toContain("default-src 'none'");
  expect(csp).not.toMatch(/https?:|unsafe-/);
});

test('reload discards the secret and keeps nothing', async ({ page }) => {
  await ready(page);
  const first = await readSecrets(page);
  await page.locator('#readable-reveal').click();
  await page.reload();
  await expect(page.locator('#deal')).toBeEnabled();
  await expect(page.locator('#readable-value')).toHaveText('Hidden');
  const html = await page.content();
  expect(html.includes(first.readable)).toBe(false);
  expect(page.url().includes('?')).toBe(false);
  const second = await readSecrets(page);
  expect(second.readable === first.readable).toBe(false);
});

test('a corrupt word list stops generation', async ({ page }) => {
  await page.route('**/eff_large_wordlist.txt', (route) =>
    route.fulfill({ status: 200, contentType: 'text/plain', body: '11111\tabacus\n' }));
  await page.goto('/');
  await expect(page.getByRole('alert')).toContainText('failed verification');
  await expect(page.locator('#deal')).toBeDisabled();
});
