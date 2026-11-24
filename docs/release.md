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
| `site/` | The files to host. Four files: `index.html`, one stylesheet, one script, one wordlist script. |
| `passphrase-deck-<version>-static.zip` | The same files, for upload to a host. |
| `passphrase-deck-<version>-offline.zip` | The same files in one folder, plus `OFFLINE-USAGE.txt`. |
| `release-manifest.json` | The SHA-256 sum of each file and each archive. |
| `SHA256SUMS` | The same sums in the common checksum format. |

The build is deterministic. Two builds from the same source give the same
bytes. `verify_release.py --self-test` proves this.

The packaged layout uses classic scripts. The wordlist is a script, not a
fetched file. So the page needs no request after it loads. It opens from a
local file in a browser. The page still checks the wordlist SHA-256 sum.
The asset names contain a short hash. Use long caching for them.

## Standalone download and PWA

The standalone download is the supported offline path. This release has no
PWA: no manifest and no service worker. A service worker would add a cache
that the host can update. The host could then replace the code on a later
visit. The benefit is small, because the standalone download already works
without a network. Add a PWA only if a phone test shows a real need. Then
cache only the four site files, test the cache contents and the update path,
and document the update risk.

## Offline use

1. Download the offline zip. Compare its SHA-256 sum with `SHA256SUMS`.
2. Unpack it. Check the folder:
   `python3 scripts/verify_release.py --check-folder DIR --manifest release-manifest.json`.
3. Open `index.html` in a browser. A `file://` page is a normal page. It
   needs no server.
4. Browsers can block clipboard access for local files. The page then says
   that copy failed. Use Reveal, select the text and copy it by hand.

The automated test opens the packaged layout from a local file with the
network off. It deals, reveals, copies and checks that no request is made.
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

Send this header with `index.html`:

```text
Content-Security-Policy: default-src 'none'; script-src 'self'; style-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'
Cache-Control: no-cache
```

The policy denies everything by default. It allows scripts and styles from
the same origin only. It grants no connection, object, base, form or
frame-ancestor permission. The shipped files need no image or manifest
allowance. Add one only if a later file needs it.

Send this header with the hashed asset files:

```text
Cache-Control: public, max-age=31536000, immutable
```

The hash in each file name makes this safe. A new release uses new names.

Use a protected deployment path. Only the owner or a named delegate can
upload. Use two-factor sign-in for the host account. Upload only files from a
verified build. Keep an audit log outside this repository.

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

It fails on missing evidence, an open finding, a failed device check, a TLS
failure, a missing header, an outside origin or a byte mismatch. It fetches
each file in the manifest and compares its SHA-256 sum. It checks the
headers and runs the static checks on the hosted bytes.

To test generation and copy against the hosted page, run the offline tests
with the hosted address:

```sh
cd tests/browser
DECK_SITE_URL=https://dullroar.com/passphrase.html npx --no-install playwright test offline.spec.js
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
    "assets": { "index.html": "<SHA-256>", "<other files>": "<SHA-256>" }
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
`Android Chrome`. The `assets` map is the `assets` map of the manifest.

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
5. Deploy the verified files to the host. Set the headers above.
6. Write `docs/release-evidence.json`. Run the production verifier. Start
   step 05 only when all of this is complete.

## Reproduce from source

1. Check out the reviewed revision.
2. Run `python3 scripts/verify_wordlist.py`.
3. Run the build. Compare `SHA256SUMS` with the published sums.
