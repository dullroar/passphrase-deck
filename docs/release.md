# Release guide

This guide tells the operator how to build, check, review and host the
Passphrase Deck release. It also lists what must happen before step 05.

## What the build makes

Run the build. Put the output outside the repository.

```sh
python3 scripts/package_release.py --out "$RALPH_WORK/release"
python3 scripts/verify_release.py --verify "$RALPH_WORK/release"
```

The build reads only an explicit list of source files:
`web/index.html`, `web/style.css`, `web/core.js`, `web/app.js` and
`data/eff_large_wordlist.txt`. It checks the wordlist hash first.

The output folder holds:

| File | Purpose |
| --- | --- |
| `passphrase.html` | The production file. One self-contained page. Copy only this file to the site root. |
| `site/` | The multi-file layout. Four files: `index.html`, one stylesheet, one script, one wordlist script. |
| `passphrase-deck-<version>-static.zip` | The multi-file layout, as a zip. |
| `passphrase-deck-<version>-offline.zip` | `passphrase.html` plus `OFFLINE-USAGE.txt`. |
| `release-manifest.json` | The SHA-256 sum of each file and each archive. |
| `SHA256SUMS` | The same sums in the common checksum format. One list covers every artifact. |

The build is deterministic. Two builds from the same source give the same
bytes. `verify_release.py --self-test` proves this.

## The single file

`passphrase.html` holds the stylesheet in one `<style>` element. It holds
the wordlist and the deck script in one inline `<script>` at the end of the
body. It loads no other file and makes no request.

The meta CSP allows each inline block by its SHA-256 hash:

```text
default-src 'none'; script-src 'sha256-<hash>'; style-src 'sha256-<hash>'; base-uri 'none'; form-action 'none'
```

The build computes each hash from the exact block text. The policy has no
`unsafe-inline`, no `unsafe-eval` and no `'self'`. It has no `connect-src`.
A script or style that an attacker injects has a different hash. The
browser blocks it. The verifier checks that the hashes match, that there is
exactly one inline script and one inline style, that no inline event
handler or outside origin exists, and that the embedded wordlist hash is
unchanged.

The offline zip holds the one file in place of the multi-file layout. The
static zip keeps the multi-file layout for hosts that want it.

The multi-file layout uses classic scripts. The wordlist is a script, not a
fetched file. So the page needs no request after it loads. It opens from a
local file in a browser. The page still checks the wordlist SHA-256 sum.
The multi-file asset names contain a short hash. Use long caching for them
only if you host that layout.

## Standalone download and PWA

The standalone download is the supported offline path. This release has no
PWA: no manifest and no service worker. A service worker would add a cache
that the host can update. The host could then replace the code on a later
visit. The benefit is small, because the standalone download already works
without a network. Add a PWA only if a phone test shows a real need. Then
cache only the one file, test the cache contents and the update path,
and document the update risk.

## Offline use

1. Download the offline zip. Compare its SHA-256 sum with `SHA256SUMS`.
2. Unpack it. Check the folder:
   `python3 scripts/verify_release.py --check-folder DIR --manifest release-manifest.json`.
3. Open `passphrase.html` in a browser. A `file://` page is a normal page. It
   needs no server.
4. Browsers can block clipboard access for local files. The page then says
   that copy failed. Use Reveal, select the text and copy it by hand.

The automated tests open both layouts from a local file with the network
off. They also open `passphrase.html` from a local server with every other
request blocked. They deal, reveal, copy and check that no request is made.
They also check that the CSP blocks an injected inline script and style.
The browser tests use Chromium. The operator must repeat the check on real
phones (see the checklist).

## Host headers

Serve the site over HTTPS only. Send these headers for every file:

```text
Strict-Transport-Security: max-age=31536000
Referrer-Policy: no-referrer
X-Content-Type-Options: nosniff
```

Add `includeSubDomains` only after you review every subdomain. Add
`preload` only after that review and a deliberate choice.

Send this header with `passphrase.html`:

```text
Cache-Control: no-cache
```

The file has a fixed name, so the browser must revalidate it. A cached old
copy would hide a new release.

A host header CSP is optional. The file has a meta CSP that already denies
everything except its two hashed inline blocks. If you send a header CSP
too, use the same hashes from the file and add `frame-ancestors`. A meta CSP
cannot set `frame-ancestors`. A header can:

```text
Content-Security-Policy: default-src 'none'; script-src 'sha256-<hash>'; style-src 'sha256-<hash>'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'
```

Never use `'self'`, `unsafe-inline` or `unsafe-eval`. Update the hashes for
every release. The production verifier checks a header CSP when it is
present.

Copy the one file `passphrase.html` to the site root. Do not link to it
from an index page. Do not copy the `site/` folder.

Use a protected deployment path. Only the owner or a named delegate can
upload. Use two-factor sign-in for the host account. Upload only the file
from a verified build. Keep an audit log outside this repository.

## Dependency scanning

The site has no runtime dependency. The test tools are pinned in
`tests/browser/package-lock.json`. CI runs `npm audit --audit-level=high` on
them. Update a pin only with a reviewed change.

## Check a production host

The verifier only reads. Run it from a checkout of the reviewed revision:

```sh
python3 scripts/verify_release.py \
  --production https://dullroar.com/passphrase.html \
  --evidence docs/release-evidence.json \
  --manifest "$RALPH_WORK/release/release-manifest.json"
```

The `--manifest` flag is required. The verifier refuses to run without it.
The manifest gives the release digest. Without it, the verifier cannot prove
that the host delivers the reviewed bytes.

It fails on missing evidence, an open finding, a failed device check, a TLS
failure, a missing header, an outside origin, an inline block that the
meta CSP does not cover or a byte mismatch. It fetches `passphrase.html`
and compares its SHA-256 sum with the manifest. It checks the headers and
runs the single-file static checks on the hosted bytes. It does not follow
a redirect to another URL.

### Delivered artifact: rule to check

Each rule in the "Delivered artifact" section of `SPEC.md` maps to a check.

| Rule | Check |
| --- | --- |
| No external executable resource | `check_single` finds an external script, link, frame, object, `<base>`, absolute URL, `javascript:` URL or another loaded file. |
| No network request from the application | `check_js` bans `fetch` of a non-local URL, `XMLHttpRequest`, `WebSocket`, `EventSource`, `sendBeacon` and dynamic import. The CSP has no `connect-src` and `default-src 'none'`. |
| No analytics or telemetry | The checks above, plus a check for the `ping` attribute and for an external image or media source. The browser tests also count requests. |
| Restrictive CSP | `check_csp` needs the exact hashes and bans `'self'`, `unsafe-inline` and `unsafe-eval`. It checks a header CSP when the host sends one. |
| Works offline | `check_single` needs one self-contained file. The browser tests open it with the network off. The operator checks it on real phones. |
| Matches a published digest | The verifier compares the SHA-256 sum of the hosted bytes with the manifest. `--manifest` is required. |

To test generation and the CSP against the hosted page, run the server
tests with the hosted address. All other requests stay blocked:

```sh
cd tests/browser
DECK_SITE_URL=https://dullroar.com/passphrase.html npx --no-install playwright test single.spec.js -g "server"
```

## Evidence file

Step 05 reads `docs/release-evidence.json`. Write only sanitized facts. Use
roles, not names. Never write a generated value. The file has four parts:

```json
{
  "candidate": {
    "revision": "<40-character Git revision>",
    "version": "<version>",
    "manifest_sha256": "<SHA-256 of release-manifest.json>",
    "assets": { "passphrase.html": "<SHA-256>" }
  },
  "review": {
    "candidate_revision": "<same revision>",
    "date": "YYYY-MM-DD",
    "reviewer_role": "independent reviewer",
    "disposition": "approved",
    "unresolved_findings": 0
  },
  "devices": [
    {
      "platform": "iOS Safari",
      "real_device": true,
      "result": "pass",
      "offline_result": "pass",
      "os_version": "<version>",
      "mode_tested": "<browser tab, home screen, or local file>",
      "install_behavior": "<what the system offered and did>",
      "date": "YYYY-MM-DD",
      "candidate_revision": "<same revision>"
    }
  ],
  "deployment": {
    "deployed_revision": "<same revision>",
    "authorized": true,
    "authorized_by_role": "owner",
    "url": "https://dullroar.com/passphrase.html",
    "date": "YYYY-MM-DD"
  }
}
```

The `devices` list needs one entry for `iOS Safari` and one for
`Android Chrome`. The `assets` map is the `single_file` map of the manifest.

## Operator checklist

1. Build and verify the release. Record the revision and the sums.
2. Give an independent reviewer the exact revision, the release folder and
   `SHA256SUMS`. Resolve every finding. Rebuild and rerun the gates after
   any change.
3. On a real iPhone with Safari and a real Android phone with Chrome, test
   the candidate. Check deal, reveal, copy, hand copy, offline use and the
   home-screen option. Record the mode and any operating-system limit.
   Emulator results can add to this evidence. They cannot replace it.
4. Decide which source files and artifacts may be public. The repository
   license is proprietary. The wordlist is CC BY 4.0 and needs attribution.
   Publish only what you authorize.
5. Copy the verified `passphrase.html` to the site root. Set the headers
   above. Do not link to it from an index page.
6. Write `docs/release-evidence.json`. Run the production verifier. Start
   step 05 only when all of this is complete.

## Reproduce from source

1. Check out the reviewed revision.
2. Run `python3 scripts/verify_wordlist.py`.
3. Run the build. Compare `SHA256SUMS` with the published sums.
