import {
  DEFAULT_SYMBOLS, DIGEST, PolicyError, digestHex, generate, parseWordlist, validateSymbols,
} from './core.js';

const $ = (id) => document.getElementById(id);
const FORMATS = ['readable', 'compact'];
const HIDDEN = 'Hidden';

// Secrets live only in this closure. The DOM holds a secret only while revealed.
let secrets = { readable: null, compact: null };
let revealed = { readable: false, compact: false };
let words = null;

function say(message) {
  $('status').textContent = message;
}

function showError(message) {
  const box = $('error');
  box.textContent = message;
  box.hidden = !message;
}

function render(name) {
  const value = secrets[name];
  const shown = revealed[name] && value !== null;
  $(`${name}-value`).textContent = shown ? value : HIDDEN;
  const button = $(`${name}-reveal`);
  button.setAttribute('aria-pressed', String(shown));
  button.textContent = `${shown ? 'Hide' : 'Reveal'} ${name}`;
  button.disabled = value === null;
  $(`${name}-copy`).disabled = value === null;
}

function clearSecrets() {
  secrets = { readable: null, compact: null };
  revealed = { readable: false, compact: false };
  FORMATS.forEach(render);
}

function readInt(id) {
  const text = $(id).value.trim();
  return /^\d{1,4}$/.test(text) ? Number(text) : NaN;
}

// Show the state of the symbol field. A bad set stops the deal.
function checkSymbols() {
  const box = $('symbols-error');
  const input = $('symbols');
  try {
    validateSymbols(input.value);
    box.textContent = '';
    box.hidden = true;
    input.removeAttribute('aria-invalid');
    return true;
  } catch (error) {
    box.textContent = `${error.message} No passphrase is dealt until you fix the set.`;
    box.hidden = false;
    input.setAttribute('aria-invalid', 'true');
    return false;
  }
}

function deal() {
  clearSecrets();
  showError('');
  if (!words) return;
  if (!checkSymbols()) {
    say('');
    return;
  }
  try {
    const pair = generate(words, {
      minimum: readInt('minimum'),
      maximum: readInt('maximum'),
      entropy: readInt('entropy'),
      capitalize: $('capitalize').checked,
      symbols: $('symbols').value,
    });
    secrets = { readable: pair.readable, compact: pair.compact };
    FORMATS.forEach(render);
    say('New pair dealt. Both formats are hidden. They are one secret.');
  } catch (error) {
    say('');
    if (error instanceof PolicyError) showError(error.message);
    else if (error && error.code === 'RANDOM_LIMIT') showError('Random generation failed. Try again.');
    else showError('Generation failed. No passphrase was made.');
  }
}

function toggle(name) {
  revealed[name] = !revealed[name];
  render(name);
  say(revealed[name] ? `The ${name} format is shown.` : `The ${name} format is hidden.`);
}

async function copy(name) {
  const value = secrets[name];
  if (value === null) return;
  try {
    await navigator.clipboard.writeText(value);
    say(`Copied the ${name} format. The page does not clear the clipboard.`);
  } catch {
    say(`Copy failed. The browser denied clipboard access. Reveal the ${name} format and copy it by hand.`);
  }
}

async function start() {
  try {
    // The packaged release embeds the wordlist in a script, so it needs no
    // request and works from a local file. The source layout fetches it.
    const embedded = globalThis.PASSPHRASE_DECK_WORDLIST;
    let buffer;
    if (typeof embedded === 'string') {
      buffer = new TextEncoder().encode(embedded).buffer;
    } else {
      const response = await fetch('eff_large_wordlist.txt', { cache: 'no-store', credentials: 'omit' });
      if (!response.ok) throw new Error('fetch failed');
      buffer = await response.arrayBuffer();
    }
    if (globalThis.crypto && crypto.subtle && (await digestHex(buffer)) !== DIGEST) {
      throw new Error('digest mismatch');
    }
    words = parseWordlist(new TextDecoder('ascii', { fatal: true }).decode(buffer));
  } catch {
    showError('The word list failed verification. The app cannot make passphrases.');
    return;
  }
  $('deal').disabled = false;
  deal();
}

// Secret lifecycle (see SPEC.md). Dropping references is best-effort disposal.
// It is not secure memory erasure.
function endSecret(message) {
  clearSecrets();
  if (message) say(message);
}

$('deal').addEventListener('click', deal);
$('preset').addEventListener('click', () => {
  $('capitalize').checked = true;
  endSecret('Restrictive-site preset on: first letters are capitalized. The old passphrase is cleared. Deal again to apply it.');
});
$('symbols').addEventListener('input', checkSymbols);
$('symbols-reset').addEventListener('click', () => {
  $('symbols').value = DEFAULT_SYMBOLS;
  checkSymbols();
  endSecret('Separator symbols reset to the default. The old passphrase is cleared. Deal again to apply them.');
});
// Any change to a generation setting clears the secret. An invalid setting
// clears it too, and the deal stays stopped until the setting is fixed.
$('settings').addEventListener('input', () => {
  endSecret('A setting changed. The old passphrase is cleared. Deal again.');
});
$('settings').addEventListener('change', () => {
  endSecret('A setting changed. The old passphrase is cleared. Deal again.');
});
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'hidden') endSecret('The tab was hidden. The passphrase is cleared. Deal again.');
});
window.addEventListener('pagehide', () => endSecret(''));
window.addEventListener('pageshow', (event) => {
  if (event.persisted) endSecret('The page was restored. The passphrase is cleared. Deal again.');
});
$('settings').addEventListener('submit', (event) => event.preventDefault());
for (const name of FORMATS) {
  $(`${name}-reveal`).addEventListener('click', () => toggle(name));
  $(`${name}-copy`).addEventListener('click', () => copy(name));
}
FORMATS.forEach(render);
start();
