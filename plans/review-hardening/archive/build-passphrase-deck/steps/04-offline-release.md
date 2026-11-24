---
id: 04-offline-release
status: done
depends_on: [03-static-web]
touches:
  - README.md
  - docs/README.md
  - docs/release.md
  - scripts/package_release.py
  - scripts/verify_release.py
  - scripts/AGENTS.md
  - web/manifest.webmanifest
  - web/service-worker.js
  - web/index.html
  - web/app.js
  - tests/browser/**
  - .github/workflows/test.yml
  - plans/build-passphrase-deck/steps/04-offline-release.md
lane: none
gate: python3 scripts/verify_wordlist.py && python3 -m unittest discover -s tests -p 'test_*.py' && (cd tests/browser && npm ci && npx --no-install playwright install chromium && npm test) && python3 scripts/verify_release.py --self-test && python3 scripts/check_context.py && git diff --check
evidence: gate passed 2026-11-24 (driver-verified)
claimed_by: claude cli-default
claimed_at: "2026-11-24T02:08:52Z"
---

# Package and verify the offline release

Build versioned static and offline artifacts from an explicit list of
application assets and the pinned wordlist. Produce SHA-256 checksums
and usage instructions. Keep generated archives outside Git. Verify an
offline copy can run without any server or external network and record
how the browser opens it. Test generation and copy after network isolation
using the packaged asset layout. Preserve a usable path when local-file
clipboard access is unavailable.

Prefer a standalone download. An optional PWA may cache only explicit
application assets and the wordlist. If added, test cache contents,
updates, and offline use. Document the risk that the host can replace the
code on update.

Make `scripts/verify_release.py --self-test` build twice in temporary
directories, verify checksums and deterministic contents, detect a changed
asset, and run the release static checks. Check runtime asset origins and
unsafe inline execution. Implement the step 05 production verifier and
test that it refuses missing or mismatched review and device evidence.
Add the product gate to CI with pinned test
dependencies. Document how the operator checks approved production URLs,
headers, and bytes using the verifier and the candidate manifest.

Document HTTPS, HSTS after a subdomain review, and a restrictive header
CSP adapted to the actual assets. Require same-origin scripts and styles.
Use a deny-by-default policy with no connection, object, base, form, or
frame-ancestor permissions. Add manifest or image allowances only if the
shipped assets need them. Use `Referrer-Policy: no-referrer`,
`X-Content-Type-Options: nosniff`, versioned caching for immutable assets,
and a protected deployment path. Keep runtime scripts and resources free
of external origins. Include dependency scanning where applicable.

Update the README with installation and hosting, phone bookmarks and home
screen options, offline verification, the password-manager workflow,
compatibility mode, and the threat model. Document reproduction from
source and give the operator a checklist for independent review, iOS
Safari and Android Chrome evidence, and authorized publication of source
and checksums. Record gate evidence and stop for the operator handoff.

## Resume notes

Work is complete. Operator handoff is open (see docs/release.md):

- Independent review of the exact release candidate and checksums.
- Real iOS Safari and Android Chrome evidence.
- Owner authorization of deployment and publication.
- Then write `docs/release-evidence.json` and start step 05.

Design notes: the release uses one classic-script layout (the wordlist is a
script) so it opens from a local file and needs no `connect-src`. The
packaged scripts are made from `web/core.js` and `web/app.js` at build time.
`web/app.js` reads the wordlist from `PASSPHRASE_DECK_WORDLIST` when set.
The production verifier is `verify_release.py --production`.
