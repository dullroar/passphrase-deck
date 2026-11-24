// Core tests. They use public fixtures and controlled ranks. No test prints a real secret.
import { test, expect } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  DIGEST, MAX_DRAWS, PolicyError, RandomLimitError, completions, digestHex,
  parseWordlist, randBelow, selectPolicy, unrank,
} from '../../web/core.js';

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, '../..');
const raw = readFileSync(path.join(repo, 'web/eff_large_wordlist.txt'));
const words = parseWordlist(raw.toString('ascii'));
const fixture = JSON.parse(readFileSync(path.join(repo, 'tests/fixtures/parity.json'), 'utf8'));

test('web wordlist is identical to the pinned data file and digest', async () => {
  expect(await digestHex(raw)).toBe(DIGEST);
  expect(raw.equals(readFileSync(path.join(repo, 'data/eff_large_wordlist.txt')))).toBe(true);
});

test('wordlist parser rejects malformed input', () => {
  const text = raw.toString('ascii');
  expect(() => parseWordlist(text.slice(0, -1))).toThrow();
  expect(() => parseWordlist(text.replace('11111\t', '11112\t'))).toThrow();
  expect(() => parseWordlist(text.replace(/\n$/, '\nextra\n'))).toThrow();
  expect(() => parseWordlist(null)).toThrow();
});

test('fixture vectors match the Python reference', () => {
  const suffix = completions(fixture.words, fixture.word_count, fixture.digits,
    fixture.minimum, fixture.maximum);
  for (const vector of fixture.vectors) {
    const out = unrank(fixture.words, fixture.word_count, fixture.digits,
      BigInt(vector.rank), suffix);
    expect(out.readable === vector.readable && out.compact === vector.compact).toBe(true);
  }
});

test('real wordlist ranks match Python, with and without capitalization', () => {
  const ranks = [0n, 1n, 999999n, 123456789012345678n];
  const code = [
    'import sys, json',
    `sys.path.insert(0, ${JSON.stringify(path.join(repo, 'python'))})`,
    'import passphrase as p',
    'w = p.load_words()',
    'out = []',
    'for min_, max_, ent in ((12, 32, 64), (12, 48, 80)):',
    '    c, d, n, s = p.select_policy(w, min_, max_, ent)',
    `    for r in ${JSON.stringify(ranks.map(String))}:`,
    '        for cap in (False, True):',
    '            out.append(list(p._unrank(w, c, d, int(r) % n, s, cap)))',
    'print(json.dumps(out))',
  ].join('\n');
  const python = JSON.parse(execFileSync('python3', ['-I', '-c', code], { encoding: 'utf8' }));
  const js = [];
  for (const [min, max, ent] of [[12, 32, 64], [12, 48, 80]]) {
    const { count, digits, outputs, suffix } = selectPolicy(words, min, max, ent);
    for (const r of ranks) {
      for (const cap of [false, true]) {
        const o = unrank(words, count, digits, r % outputs, suffix, cap);
        js.push([o.readable, o.compact]);
      }
    }
  }
  expect(js.length).toBe(python.length);
  expect(JSON.stringify(js) === JSON.stringify(python)).toBe(true);
});

test('capitalization changes only first letters and keeps lengths', () => {
  const { count, digits, suffix } = selectPolicy(words, 12, 32, 64);
  const plain = unrank(words, count, digits, 424242n, suffix, false);
  const caps = unrank(words, count, digits, 424242n, suffix, true);
  expect(caps.readable.length).toBe(plain.readable.length);
  expect(caps.readable.toLowerCase()).toBe(plain.readable);
  expect(caps.compact).toBe(caps.readable.replaceAll(' ', ''));
  expect(caps.readable.split('_ ').every((w) => /^[A-Z]/.test(w))).toBe(true);
});

test('both formats meet length bounds at extreme ranks', () => {
  for (const [min, max, ent] of [[12, 32, 64], [12, 48, 80]]) {
    const { count, digits, outputs, suffix } = selectPolicy(words, min, max, ent);
    for (const r of [0n, outputs - 1n, outputs / 2n]) {
      const o = unrank(words, count, digits, r, suffix, true);
      expect(o.compact.length >= min && o.readable.length <= max).toBe(true);
    }
    expect(() => unrank(words, count, digits, outputs, suffix)).toThrow();
  }
});

test('randBelow rejects biased values and bad input', () => {
  const stream = (values) => { let i = 0; return () => Uint8Array.of(values[i++]); };
  expect(randBelow(3n, stream([255, 254]))).toBe(2n);
  expect(randBelow(1n, stream([200]))).toBe(0n);
  expect(randBelow(255n, stream([200]))).toBe(200n);
  let draws = 0;
  expect(() => randBelow(3n, () => { draws += 1; return Uint8Array.of(255); }))
    .toThrow(RandomLimitError);
  expect(draws).toBe(MAX_DRAWS);
  for (const bad of [0n, -1n, 3, '3']) expect(() => randBelow(bad, stream([1]))).toThrow();
  expect(() => randBelow(3n, () => new Uint8Array(2))).toThrow();
  expect(() => randBelow(3n, () => [1])).toThrow();
});

test('randBelow uses multi-byte draws for large bounds', () => {
  const n = 1n << 70n;
  const value = randBelow(n, (size) => new Uint8Array(size).fill(1));
  expect(value).toBe(0x010101010101010101n);
});

test('policy accepts documented policies', () => {
  expect(selectPolicy(words, 12, 32, 64).count).toBe(4);
  expect(selectPolicy(words, 12, 48, 80).outputs >= 1n << 80n).toBe(true);
});

test('policy rejects invalid input', () => {
  const bad = [[12.5, 32, 64], [20, 12, 64], [0, 32, 64], [12, 129, 64], [12, 32, 63],
    [12, 32, 129], [NaN, 32, 64], ['12', 32, 64]];
  for (const args of bad) {
    expect(() => selectPolicy(words, ...args)).toThrow(PolicyError);
    try { selectPolicy(words, ...args); } catch (e) { expect(e.code).toBe('POLICY_INVALID'); }
  }
});

test('unsupported policy suggests a feasible change without lowering the floor first', () => {
  let error;
  try { selectPolicy(words, 12, 14, 64); } catch (e) { error = e; }
  expect(error.code).toBe('POLICY_UNSUPPORTED');
  expect(error.suggestion.maximum > 14).toBe(true);
  expect(() => selectPolicy(words, 12, error.suggestion.maximum, 64)).not.toThrow();
  expect(error.message).toContain('Try a maximum length');
});
