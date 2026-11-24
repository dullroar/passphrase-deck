// Secret lifecycle tests. Assertions compare booleans so a failure never prints a real secret.
import { test, expect } from '@playwright/test';

async function ready(page) {
  await page.goto('/');
  await expect(page.locator('#deal')).toBeEnabled();
}

// Reveal one format and return its text. The secret stays shown.
async function show(page) {
  await page.locator('#readable-reveal').click();
  return page.locator('#readable-value').textContent();
}

async function expectCleared(page, secret) {
  await expect(page.locator('#readable-value')).toHaveText('Hidden');
  await expect(page.locator('#compact-value')).toHaveText('Hidden');
  await expect(page.locator('#readable-reveal')).toBeDisabled();
  await expect(page.locator('#compact-reveal')).toBeDisabled();
  await expect(page.locator('#readable-copy')).toBeDisabled();
  await expect(page.locator('#compact-copy')).toBeDisabled();
  const html = await page.content();
  expect(html.includes(secret)).toBe(false);
}

test('a change to each generation setting clears the secret', async ({ page }) => {
  await ready(page);
  const changes = [
    () => page.locator('#minimum').fill('13'),
    () => page.locator('#maximum').fill('40'),
    () => page.locator('#entropy').fill('70'),
    () => page.locator('#capitalize').check(),
    () => page.locator('#symbols').fill('%&'),
    () => page.locator('#preset').click(),
    () => page.locator('#symbols-reset').click(),
  ];
  for (const change of changes) {
    await page.locator('#deal').click();
    const secret = await show(page);
    expect(secret !== 'Hidden').toBe(true);
    await change();
    await expectCleared(page, secret);
  }
});

test('an invalid setting clears the secret and does not deal', async ({ page }) => {
  await ready(page);
  const secret = await show(page);
  await page.locator('#entropy').fill('40');
  await expectCleared(page, secret);
  await expect(page.locator('#deal')).toBeDisabled();
  await expect(page.locator('#policy-status')).toContainText('malformed');
  await expectCleared(page, secret);
  await page.locator('#entropy').fill('64');
  await page.locator('#symbols').fill('a');
  await expect(page.locator('#deal')).toBeDisabled();
  await expect(page.locator('#symbols-error')).toBeVisible();
  await expectCleared(page, secret);
});

test('a new deal clears the old secret first', async ({ page }) => {
  await ready(page);
  const first = await show(page);
  await page.locator('#deal').click();
  await expect(page.locator('#readable-value')).toHaveText('Hidden');
  await expect(page.locator('#readable-reveal')).toHaveAttribute('aria-pressed', 'false');
  const html = await page.content();
  expect(html.includes(first)).toBe(false);
});

test('a failed deal leaves no secret', async ({ page }) => {
  await ready(page);
  const secret = await show(page);
  await page.locator('#maximum').fill('14');
  await expect(page.locator('#deal')).toBeDisabled();
  await expect(page.locator('#policy-status')).toContainText('Try a maximum length');
  await expectCleared(page, secret);
  const error = await page.locator('#policy-status').textContent();
  expect(error.includes(secret)).toBe(false);
});

test('a hidden tab clears the secret', async ({ page }) => {
  await ready(page);
  const secret = await show(page);
  await page.evaluate(() => {
    Object.defineProperty(document, 'visibilityState', { value: 'hidden', configurable: true });
    document.dispatchEvent(new Event('visibilitychange'));
  });
  await expectCleared(page, secret);
});

test('a visible tab does not clear the secret', async ({ page }) => {
  await ready(page);
  await page.locator('#readable-reveal').click();
  await page.evaluate(() => {
    Object.defineProperty(document, 'visibilityState', { value: 'visible', configurable: true });
    document.dispatchEvent(new Event('visibilitychange'));
  });
  await expect(page.locator('#readable-value')).not.toHaveText('Hidden');
});

test('pagehide clears the secret', async ({ page }) => {
  await ready(page);
  const secret = await show(page);
  await page.evaluate(() => window.dispatchEvent(new Event('pagehide')));
  await expectCleared(page, secret);
});

test('pageshow with persisted true clears the secret', async ({ page }) => {
  await ready(page);
  const secret = await show(page);
  await page.evaluate(() => window.dispatchEvent(new PageTransitionEvent('pageshow', { persisted: true })));
  await expectCleared(page, secret);
});

test('pageshow with persisted false keeps the secret', async ({ page }) => {
  await ready(page);
  await page.locator('#readable-reveal').click();
  await page.evaluate(() => window.dispatchEvent(new PageTransitionEvent('pageshow', { persisted: false })));
  await expect(page.locator('#readable-value')).not.toHaveText('Hidden');
});

test('a copy failure keeps the secret and says so', async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: () => Promise.reject(new DOMException('denied', 'NotAllowedError')) },
    });
  });
  await ready(page);
  const secret = await show(page);
  await page.locator('#readable-copy').click();
  await expect(page.locator('#status')).toContainText('Copy failed');
  await expect(page.locator('#readable-value')).not.toHaveText('Hidden');
  await expect(page.locator('#readable-copy')).toBeEnabled();
  const status = await page.locator('#status').textContent();
  expect(status.includes(secret)).toBe(false);
});

test('copy does not clear the clipboard or the secret', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await ready(page);
  const secret = await show(page);
  await page.locator('#readable-copy').click();
  await expect(page.locator('#status')).toContainText('does not clear the clipboard');
  await page.waitForTimeout(300);
  expect(await page.evaluate(() => navigator.clipboard.readText()) === secret).toBe(true);
  await expect(page.locator('#readable-value')).not.toHaveText('Hidden');
});

test('logs and errors never hold a secret', async ({ page }) => {
  const logs = [];
  page.on('console', (m) => logs.push(m.text()));
  page.on('pageerror', (e) => logs.push(String(e)));
  await ready(page);
  const secret = await show(page);
  await page.locator('#maximum').fill('14');
  await expect(page.locator('#deal')).toBeDisabled();
  const error = await page.locator('#policy-status').textContent();
  expect([error, ...logs].some((text) => text.includes(secret))).toBe(false);
});

test('the notice says choosing a result lowers the strength', async ({ page }) => {
  await ready(page);
  const notice = await page.locator('#choice-notice').textContent();
  expect(/passphrase only/.test(notice) && /strength is lower/.test(notice)).toBe(true);
});

test('the policy status names each state in words and gates Deal', async ({ page }) => {
  await ready(page);
  const status = page.locator('#policy-status');
  await expect(status).toHaveAttribute('role', 'status');
  await expect(status).toHaveAttribute('aria-live', 'polite');
  // Valid.
  await expect(status).toContainText('Policy valid');
  await expect(status).toContainText('bits');
  await expect(page.locator('#deal')).toBeEnabled();
  // Unsupported. The advice stays. No deal is needed.
  await page.locator('#maximum').fill('14');
  await expect(status).toContainText('Policy unsupported');
  await expect(status).toContainText('Try a maximum length');
  await expect(page.locator('#deal')).toBeDisabled();
  // Malformed.
  await page.locator('#maximum').fill('10');
  await expect(status).toContainText('Policy malformed');
  await expect(page.locator('#deal')).toBeDisabled();
  await page.locator('#maximum').fill('32');
  await page.locator('#symbols').fill('a');
  await expect(status).toContainText('Policy malformed');
  await expect(page.locator('#deal')).toBeDisabled();
  // Back to valid.
  await page.locator('#symbols-reset').click();
  await expect(status).toContainText('Policy valid');
  await expect(page.locator('#deal')).toBeEnabled();
});

test('preflight makes no random call in the page', async ({ page }) => {
  await page.addInitScript(() => {
    window.__draws = 0;
    const original = crypto.getRandomValues.bind(crypto);
    crypto.getRandomValues = (array) => { window.__draws += 1; return original(array); };
  });
  await page.goto('/');
  await expect(page.locator('#deal')).toBeEnabled();
  const afterLoad = await page.evaluate(() => window.__draws);
  await page.locator('#entropy').fill('70');
  await page.locator('#maximum').fill('14');
  await page.locator('#maximum').fill('32');
  await expect(page.locator('#policy-status')).toContainText('Policy valid');
  expect(await page.evaluate(() => window.__draws)).toBe(afterLoad);
});
