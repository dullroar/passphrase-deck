import { DIGEST, PolicyError, digestHex, generate, parseWordlist } from './core.js';

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

function deal() {
  clearSecrets();
  showError('');
  if (!words) return;
  try {
    const pair = generate(words, {
      minimum: readInt('minimum'),
      maximum: readInt('maximum'),
      entropy: readInt('entropy'),
      capitalize: $('capitalize').checked,
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

$('deal').addEventListener('click', deal);
$('preset').addEventListener('click', () => {
  $('capitalize').checked = true;
  say('Restrictive-site preset on: first letters are capitalized. Deal again to apply it.');
});
$('settings').addEventListener('submit', (event) => event.preventDefault());
for (const name of FORMATS) {
  $(`${name}-reveal`).addEventListener('click', () => toggle(name));
  $(`${name}-copy`).addEventListener('click', () => copy(name));
}
FORMATS.forEach(render);
start();
