---
id: 04a-single-file-release
status: pending
depends_on: [04-offline-release]
touches:
  - scripts/package_release.py
  - scripts/verify_release.py
  - scripts/AGENTS.md
  - docs/release.md
  - docs/README.md
  - README.md
  - tests/browser/**
  - plans/build-passphrase-deck/plan.md
  - plans/build-passphrase-deck/steps/04a-single-file-release.md
  - plans/build-passphrase-deck/steps/05-production-verification.md
lane: none
gate: python3 scripts/verify_wordlist.py && python3 -m unittest discover -s tests -p 'test_*.py' && (cd tests/browser && npm ci && npx --no-install playwright install chromium && npm test) && python3 scripts/verify_release.py --self-test && python3 scripts/check_context.py && git diff --check
evidence: ""
---

# Build one self-contained passphrase.html

The owner hosts the app on a minimal site. The site has no build step and
no asset folders. The host takes one file. Add a single-file build output.

Decision (owner, 2026-11-24): the production page is `passphrase.html` at
the site root. The URL is `https://dullroar.com/passphrase.html`. No index
page links to it. The earlier URL `https://dullroar.com/passphrase/` is
replaced everywhere.

## Work

1. Make `scripts/package_release.py` write `passphrase.html`. It has the
   stylesheet in one `<style>` element. It has the wordlist and the deck
   script in one inline `<script>`. It loads nothing else. Keep the build
   deterministic.
2. Replace the `script-src 'self'` and `style-src 'self'` meta CSP with
   hash sources. Compute the SHA-256 of each inline block at build time.
   Allow no `unsafe-inline` and no `unsafe-eval`. Keep every other
   deny-by-default directive. Keep `connect-src` absent.
3. Keep the multi-file layout and the offline zip. The offline zip may
   include `passphrase.html` in place of the multi-file site. Choose one
   and document it. Keep one checksum list that covers every artifact.
4. Update `verify_release.py` (self-test, static checks and production
   mode) to check the single file: hashes match the CSP, no external
   origin, no inline event handler, and the wordlist hash is unchanged.
   The production check targets the `passphrase.html` URL.
5. Run the existing browser tests against the single file. Add tests that
   load it from a `file://` URL and from a server, with the network
   blocked. Check that the CSP blocks an injected inline script.
6. Update `docs/release.md`, `README.md` and step 05 to use the new URL
   and file name. Say that the owner copies one file to the site root.
   Say that an index page must not link to it. Keep the headers advice. Say
   that a host header CSP is optional because the file has a meta CSP.

## Limits

Do not change `SPEC.md`, the wordlist or the policy logic. Do not deploy.
Record the gate result and a short note on the final file size.
