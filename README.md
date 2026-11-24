# Passphrase Deck

Passphrase Deck is a small passphrase generator for desktop and phone. Each
deal creates one secret in two formats. The readable version has spaces. The
compact version removes those ASCII spaces and keeps every other character.
Copy the format the destination accepts and save that format in your
password manager. Treat both formats as the same secret.

The browser generates locally with the browser's cryptographic random
number generator and a bundled, pinned wordlist. The page has no accounts,
analytics, or password history. A standard-library Python CLI is the
reference implementation. The planned web address is
`https://dullroar.com/passphrase.html`.

The release is prepared. The independent review, the real-phone checks and
the production check are still open. See the
[implementation plan](plans/archive/build-passphrase-deck/plan.md) and the
[release guide](docs/release.md).

## Install and host

The app is one self-contained file, `passphrase.html`. It has no server
code, no runtime dependency and no other file. Build it, then copy the one
file to the root of the site:

```sh
python3 scripts/package_release.py --out "$RALPH_WORK/release"
python3 scripts/verify_release.py --verify "$RALPH_WORK/release"
```

The page is then at `https://dullroar.com/passphrase.html`. Do not link to
it from an index page. Serve it over HTTPS with the headers in the
[release guide](docs/release.md). The file has its own meta CSP, so a host
header CSP is optional. The build output stays outside Git.

## Phone use

- **Bookmark:** open the hosted page and use the browser's bookmark option.
- **Home screen:** on iOS Safari use Share, then Add to Home Screen. On
  Android Chrome use the menu, then Add to Home screen. This makes a
  shortcut to the page. The page has no service worker.
- **Offline:** unpack the offline zip on the phone and open `passphrase.html`.
  Some phone browsers do not open local files. The real-device checklist
  records what each phone does.

## Verify an offline copy

1. Compare the zip's SHA-256 sum with the published `SHA256SUMS`.
2. Unpack it and run
   `python3 scripts/verify_release.py --check-folder DIR --manifest release-manifest.json`.
3. Open `passphrase.html`. The page works with the network off.

## Password-manager workflow

1. Open the page and press Deal another pair.
2. Press Reveal for the format you need, or press Copy.
3. Paste it into the account form and into your password manager.
4. Save one format only for each account. Both formats are the same secret.
5. Reload or close the page. The page keeps no history.

The page does not clear the clipboard. Clear it yourself.

## Compatibility mode

Some sites reject spaces or need a capital letter. Use the compact format
for sites that reject spaces. Use the restrictive-site preset to capitalize
the first letter of each word. Edit the separator symbols if a site rejects
some of them. The default set is `.,#$_!?`. Use 1 to 32 different punctuation
symbols. Do not use letters, digits or spaces. A hyphen is allowed. The CLI option is
`--symbols`. Every deal puts one symbol from your set between each pair of
words and ends with digits. Both formats meet the length range and the entropy
floor of 64 bits. If a policy cannot be met, the page shows the conflict and
a change that works. It never lowers the floor for you.

If the browser blocks the Copy button (for example on a local file), use
Reveal, select the text and copy it by hand.

## Threat model

The design protects against weak or reused human choices and against
network exposure while you generate. The page makes no request after it
loads, keeps nothing in storage and sends nothing.

It does not protect against:

- Hosted code that someone replaced. A browser runs the code it receives,
  even over HTTPS. For high-value accounts use a verified offline copy.
- Browser extensions, clipboard readers, screen capture and device malware.
- Phishing, and a site that stores or leaks your password.
- A shoulder surfer when a value is revealed.

## Reproduce from source

Check out a reviewed revision. Run `python3 scripts/verify_wordlist.py`.
Build the release. The same source gives the same bytes, so your sums must
match the published sums.

## Review and publication checklist

The [release guide](docs/release.md) lists the steps. In short:
independent review of the exact candidate, real iOS Safari and Android Chrome
evidence, then owner-authorized deployment and publication of source and
checksums.

## Repository checks

```sh
python3 scripts/build_indexes.py
python3 scripts/check_context.py
python3 scripts/verify_release.py --self-test
```

## License

See the [proprietary license](LICENSE).
