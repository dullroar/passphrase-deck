// Passphrase core. It follows SPEC.md and matches python/passphrase.py.
// It has no dependency and makes no network request.

export const DIGEST = 'addd35536511597a02fa0a9ff1e5284677b8883b83e986e43f15a3db996b903e';
export const SCHEMES = [[4, 6], [6, 2]];
export const MAX_DRAWS = 128;
export const DEFAULT_SYMBOLS = '.,#$_!?';
export const MAX_SYMBOLS = 32;
const ALLOWED_SYMBOLS = new Set('!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~');

export class PolicyError extends Error {
  constructor(code, message, suggestion = null) {
    super(message);
    this.name = 'PolicyError';
    this.code = code;
    this.suggestion = suggestion;
  }
}

export class RandomLimitError extends Error {
  constructor() {
    super('RANDOM_LIMIT');
    this.name = 'RandomLimitError';
    this.code = 'RANDOM_LIMIT';
  }
}

// Check the symbol set. Return the symbols as an array. Reject the whole set
// on any bad symbol. Name the position and code point, never the text.
export function validateSymbols(symbols) {
  if (typeof symbols !== 'string' || symbols.length < 1 || symbols.length > MAX_SYMBOLS) {
    throw new PolicyError('SYMBOLS_INVALID', `Use 1 to ${MAX_SYMBOLS} symbols.`);
  }
  const seen = new Set();
  const list = symbols.split('');
  list.forEach((char, index) => {
    const hex = char.charCodeAt(0).toString(16).toUpperCase().padStart(4, '0');
    const name = `symbol ${index + 1} (U+${hex})`;
    if (!ALLOWED_SYMBOLS.has(char)) {
      throw new PolicyError('SYMBOLS_INVALID',
        `The ${name} is not allowed. Use ASCII punctuation. Do not use letters, digits or spaces.`);
    }
    if (seen.has(char)) throw new PolicyError('SYMBOLS_INVALID', `The ${name} is repeated.`);
    seen.add(char);
  });
  return list;
}

// Check the structure of the wordlist text. Return the list of words.
export function parseWordlist(text) {
  if (typeof text !== 'string') throw new Error('wordlist verification failed');
  const lines = text.split('\n');
  if (lines.pop() !== '' || lines.length !== 7776) {
    throw new Error('wordlist verification failed');
  }
  const words = lines.map((line, index) => {
    const match = /^([1-6]{5})\t([a-z-]+)$/.exec(line);
    let code = '';
    for (let i = 0, n = index; i < 5; i += 1, n = Math.floor(n / 6)) {
      code = String((n % 6) + 1) + code;
    }
    if (!match || match[1] !== code) throw new Error('wordlist verification failed');
    return match[2];
  });
  if (new Set(words).size !== 7776) throw new Error('wordlist verification failed');
  return words;
}

// Verify the SHA-256 digest of the raw bytes when the browser offers it.
export async function digestHex(buffer) {
  const hash = await globalThis.crypto.subtle.digest('SHA-256', buffer);
  return Array.from(new Uint8Array(hash), (b) => b.toString(16).padStart(2, '0')).join('');
}

export function completions(words, count, digits, minimum, maximum) {
  const lengths = new Map();
  for (const word of words) lengths.set(word.length, (lengths.get(word.length) || 0n) + 1n);
  const memo = new Map();
  const suffix = (remaining, length) => {
    if (remaining === 0) {
      return minimum <= length + digits + count - 1 &&
        length + digits + 2 * (count - 1) <= maximum ? 1n : 0n;
    }
    const key = remaining * 1024 + length;
    if (memo.has(key)) return memo.get(key);
    let total = 0n;
    for (const [size, quantity] of lengths) total += quantity * suffix(remaining - 1, length + size);
    memo.set(key, total);
    return total;
  };
  return suffix;
}

function validBounds(minimum, maximum, entropy) {
  return [minimum, maximum, entropy].every(Number.isInteger) &&
    minimum >= 1 && minimum <= maximum && maximum <= 128 && entropy >= 64 && entropy <= 128;
}

function trySelect(words, minimum, maximum, entropy, symbolCount) {
  for (const [count, digits] of SCHEMES) {
    const suffix = completions(words, count, digits, minimum, maximum);
    const outputs = suffix(count, 0) * 10n ** BigInt(digits) *
      BigInt(symbolCount) ** BigInt(count - 1);
    if (outputs >= 1n << BigInt(entropy)) return { count, digits, outputs, suffix };
  }
  return null;
}

// Find a nearby change that keeps the entropy floor, then one that lowers it.
function suggest(words, minimum, maximum, entropy, n) {
  for (let max = maximum + 1; max <= 128; max += 1) {
    if (trySelect(words, minimum, max, entropy, n)) return { maximum: max };
  }
  for (let min = minimum - 1; min >= 1; min -= 1) {
    if (trySelect(words, min, maximum, entropy, n)) return { minimum: min };
  }
  for (let bits = entropy - 1; bits >= 64; bits -= 1) {
    if (trySelect(words, minimum, maximum, bits, n)) return { entropy: bits };
  }
  return null;
}

export function selectPolicy(words, minimum, maximum, entropy, symbols = DEFAULT_SYMBOLS) {
  if (!validBounds(minimum, maximum, entropy)) {
    throw new PolicyError('POLICY_INVALID',
      'Use whole numbers: length from 1 to 128, minimum not above maximum, entropy from 64 to 128.');
  }
  const n = validateSymbols(symbols).length;
  const found = trySelect(words, minimum, maximum, entropy, n);
  if (found) return found;
  const suggestion = suggest(words, minimum, maximum, entropy, n);
  let hint = 'No change within the allowed ranges meets the policy.';
  if (suggestion && suggestion.maximum) hint = `Try a maximum length of ${suggestion.maximum} or more.`;
  else if (suggestion && suggestion.minimum) hint = `Try a minimum length of ${suggestion.minimum} or less.`;
  else if (suggestion && suggestion.entropy) hint = `Try a minimum entropy of ${suggestion.entropy} bits or less.`;
  throw new PolicyError('POLICY_UNSUPPORTED',
    `No supported scheme meets this policy. ${hint} The entropy floor is never lowered for you.`,
    suggestion);
}

// Preflight. A pure check of the settings. It reads no random source and holds
// no secret. It reuses selectPolicy, so it cannot differ from a real deal.
// State "malformed": the settings are not well formed (POLICY_INVALID or
// SYMBOLS_INVALID). State "unsupported": no scheme meets the policy
// (POLICY_UNSUPPORTED). State "valid": it gives the scheme and the exact
// number of whole bits of the output count (the floor of log2).
export function preflight(words, { minimum, maximum, entropy, symbols = DEFAULT_SYMBOLS } = {}) {
  try {
    const { count, digits, outputs } = selectPolicy(words, minimum, maximum, entropy, symbols);
    return { state: 'valid', count, digits, bits: outputs.toString(2).length - 1 };
  } catch (error) {
    if (!(error instanceof PolicyError)) throw error;
    const state = error.code === 'POLICY_UNSUPPORTED' ? 'unsupported' : 'malformed';
    return { state, code: error.code, message: error.message };
  }
}

export function unrank(words, count, digits, rank, suffix, capitalize = false, symbols = '_') {
  const list = validateSymbols(symbols);
  const base = BigInt(list.length);
  const quotient = rank / 10n ** BigInt(digits);
  const digitRank = rank % 10n ** BigInt(digits);
  const gapSpan = base ** BigInt(count - 1);
  let tupleRank = quotient / gapSpan;
  let symbolRank = quotient % gapSpan;
  const gaps = [];
  for (let i = 0; i < count - 1; i += 1) {
    gaps.push(list[Number(symbolRank % base)]);
    symbolRank /= base;
  }
  gaps.reverse();
  const selected = [];
  let length = 0;
  for (let remaining = count - 1; remaining >= 0; remaining -= 1) {
    let found = false;
    for (const word of words) {
      const weight = suffix(remaining, length + word.length);
      if (tupleRank < weight) {
        selected.push(word);
        length += word.length;
        found = true;
        break;
      }
      tupleRank -= weight;
    }
    if (!found) throw new Error('rank outside valid range');
  }
  if (tupleRank !== 0n) throw new Error('rank outside valid range');
  const shown = capitalize ? selected.map((w) => w[0].toUpperCase() + w.slice(1)) : selected;
  const readable = shown.map((w, i) => (i < count - 1 ? `${w}${gaps[i]} ` : w)).join('') + digitRank.toString().padStart(digits, '0');
  return { readable, compact: readable.replaceAll(' ', '') };
}

// Unbiased rejection sampling. The draw function returns n random bytes.
export function randBelow(n, draw) {
  if (typeof n !== 'bigint' || n <= 0n) throw new Error('invalid random bound');
  const size = Math.max(1, Math.ceil(n.toString(2).length / 8));
  const range = 1n << BigInt(8 * size);
  const limit = range - (range % n);
  for (let i = 0; i < MAX_DRAWS; i += 1) {
    const raw = draw(size);
    if (!(raw instanceof Uint8Array) || raw.length !== size) throw new Error('random source failure');
    let value = 0n;
    for (const byte of raw) value = (value << 8n) | BigInt(byte);
    if (value < limit) return value % n;
  }
  throw new RandomLimitError();
}

function browserDraw(size) {
  const bytes = new Uint8Array(size);
  globalThis.crypto.getRandomValues(bytes);
  return bytes;
}

// Production entry point. It takes no random source.
export function generate(words, { minimum = 12, maximum = 32, entropy = 64, capitalize = false, symbols = DEFAULT_SYMBOLS } = {}) {
  const { count, digits, outputs, suffix } = selectPolicy(words, minimum, maximum, entropy, symbols);
  return unrank(words, count, digits, randBelow(outputs, browserDraw), suffix, capitalize, symbols);
}
