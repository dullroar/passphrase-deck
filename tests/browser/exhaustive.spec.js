// Exhaustive rank tests for the browser core. They use the public fixture
// tests/fixtures/exhaustive.json and a brute-force reference written here.
// The reference shares no code with the counting code in web/core.js.
import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { MAX_DRAWS, RandomLimitError, completions, randBelow, unrank } from '../../web/core.js';

const here = path.dirname(fileURLToPath(import.meta.url));
const fixture = JSON.parse(readFileSync(path.join(here, '../fixtures/exhaustive.json'), 'utf8'));

function product(items, repeat) {
  let result = [[]];
  for (let i = 0; i < repeat; i += 1) result = result.flatMap((head) => items.map((x) => [...head, x]));
  return result;
}

function bruteForce(c, capitalize = false, minimum = c.minimum, maximum = c.maximum) {
  const found = [];
  const numbers = 10 ** c.digits;
  for (const chosen of product(c.words, c.word_count)) {
    const shown = chosen.map((w) => (capitalize ? w[0].toUpperCase() + w.slice(1) : w));
    for (const gaps of product([...c.symbols], c.word_count - 1)) {
      for (let n = 0; n < numbers; n += 1) {
        let readable = '';
        for (let i = 0; i < c.word_count - 1; i += 1) readable += `${shown[i]}${gaps[i]} `;
        readable += shown[c.word_count - 1] + String(n).padStart(c.digits, '0');
        const compact = readable.replaceAll(' ', '');
        if (minimum <= compact.length && readable.length <= maximum) found.push([readable, compact]);
      }
    }
  }
  return found;
}

function unrankAll(c, capitalize = false) {
  const suffix = completions(c.words, c.word_count, c.digits, c.minimum, c.maximum);
  const total = suffix(c.word_count, 0) * 10n ** BigInt(c.digits) *
    BigInt(c.symbols.length) ** BigInt(c.word_count - 1);
  const outputs = [];
  for (let rank = 0n; rank < total; rank += 1n) {
    const out = unrank(c.words, c.word_count, c.digits, rank, suffix, capitalize, c.symbols);
    outputs.push([out.readable, out.compact]);
  }
  return { total, outputs };
}

const key = (pair) => pair.join('\u0000');

test('fixture holds several tiny cases', () => {
  expect(fixture.cases.length).toBeGreaterThanOrEqual(6);
});

test('every rank matches the brute force and the Python fixture', () => {
  for (const c of fixture.cases) {
    const { total, outputs } = unrankAll(c);
    const expected = bruteForce(c);
    expect(Number(total)).toBe(expected.length);
    expect(Number(total)).toBe(c.total);
    expect(new Set(outputs.map((p) => p[0])).size).toBe(c.total);
    expect(new Set(outputs.map((p) => p[1])).size).toBe(c.total);
    expect(new Set(outputs.map(key))).toEqual(new Set(expected.map(key)));
    expect(outputs).toEqual(c.outputs);
  }
});

test('outputs meet the length rules and split back', () => {
  for (const c of fixture.cases) {
    const word = c.words.join('|');
    const symbol = `[${[...c.symbols].map((s) => `\\${s}`).join('')}]`;
    const n = c.word_count - 1;
    const readable = new RegExp(`^(?:(?:${word})${symbol} ){${n}}(?:${word})\\d{${c.digits}}$`);
    const compact = new RegExp(`^(?:(?:${word})${symbol}){${n}}(?:${word})\\d{${c.digits}}$`);
    for (const [text, short] of unrankAll(c).outputs) {
      expect(short.length >= c.minimum && text.length <= c.maximum).toBe(true);
      expect(readable.test(text) && compact.test(short)).toBe(true);
      expect(text.replaceAll(' ', '')).toBe(short);
    }
  }
});

test('length limits remove exactly the expected outputs', () => {
  let removed = false;
  for (const c of fixture.cases) {
    const wide = bruteForce(c, false, 1, 128);
    const kept = new Set(unrankAll(c).outputs.map(key));
    const gone = wide.filter((p) => !kept.has(key(p)));
    for (const [text, short] of gone) expect(short.length < c.minimum || text.length > c.maximum).toBe(true);
    expect(kept.size + gone.length).toBe(wide.length);
    removed = removed || gone.length > 0;
  }
  expect(removed).toBe(true);
});

test('capitalization keeps the count and the distinctness', () => {
  for (const c of fixture.cases) {
    const { total, outputs } = unrankAll(c, true);
    expect(Number(total)).toBe(c.total);
    expect(new Set(outputs.map((p) => p[0])).size).toBe(c.total);
    expect(new Set(outputs.map((p) => p[1])).size).toBe(c.total);
    expect(new Set(outputs.map(key))).toEqual(new Set(bruteForce(c, true).map(key)));
  }
});

test('a rank outside the range fails', () => {
  const c = fixture.cases[0];
  const suffix = completions(c.words, c.word_count, c.digits, c.minimum, c.maximum);
  expect(() => unrank(c.words, c.word_count, c.digits, BigInt(c.total) * 1000n, suffix, false, c.symbols)).toThrow();
});

function source(values, size) {
  let index = 0;
  return (wanted) => {
    expect(wanted).toBe(size);
    const bytes = new Uint8Array(size);
    let value = values[index];
    index += 1;
    for (let i = size - 1; i >= 0; i -= 1) { bytes[i] = value % 256; value = Math.floor(value / 256); }
    return bytes;
  };
}

test('random draw at its boundaries', () => {
  // n = 1000 needs 2 bytes. The limit is 65536 - 536 = 65000.
  expect(randBelow(1000n, source([64999], 2))).toBe(999n);
  expect(randBelow(1000n, source([65000, 7], 2))).toBe(7n);
  expect(randBelow(1000n, source([65535, 1234], 2))).toBe(234n);
  expect(randBelow(1000n, source([0], 2))).toBe(0n);
  expect(randBelow(1000n, source([...Array(MAX_DRAWS - 1).fill(65000), 5], 2))).toBe(5n);
});

test('RANDOM_LIMIT after 128 draws returns no secret', () => {
  let calls = 0;
  const draw = (size) => { calls += 1; return new Uint8Array(size).fill(0).map((_, i) => (i === 0 ? 253 : 232)); };
  let caught = null;
  try { randBelow(1000n, draw); } catch (error) { caught = error; }
  expect(MAX_DRAWS).toBe(128);
  expect(caught).toBeInstanceOf(RandomLimitError);
  expect(caught.message).toBe('RANDOM_LIMIT');
  expect(calls).toBe(128);
});

test('bad bound or bad source fails', () => {
  expect(() => randBelow(0n, () => new Uint8Array(1))).toThrow();
  expect(() => randBelow(1000n, () => new Uint8Array(1))).toThrow();
});
