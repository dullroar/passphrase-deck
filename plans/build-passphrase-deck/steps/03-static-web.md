---
id: 03-static-web
status: done
depends_on: [02-python-reference]
touches:
  - web/**
  - tests/browser/**
  - plans/build-passphrase-deck/steps/03-static-web.md
lane: none
gate: python3 scripts/verify_wordlist.py && (cd tests/browser && npm ci && npx --no-install playwright install chromium && npm test) && python3 scripts/check_context.py && git diff --check
evidence: gate passed 2026-11-24 (driver-verified)
claimed_by: claude cli-default
claimed_at: "2026-11-24T02:04:08Z"
---

# Build and test the static browser app

Use plain HTML, CSS, and JavaScript with same-origin app files and a
bundled wordlist verified against the pinned source. Use the browser
CSPRNG and the accepted unbiased selection and policy logic. Generate
without an API, runtime third-party dependencies, or a network request.
If the user asks for an infeasible policy, suggest a feasible longer
maximum, permitted options, or word count that meets the entropy floor.

Provide a prominent **Deal another pair** action. Show the two formats
side by side on wide screens and stacked on phones. Make clear that this is
one secret. Give each format a separate, accessible reveal and copy
control. Keep secrets visually private by default where practical and
avoid keeping secret text in the DOM longer than needed. Report clipboard
denial accurately. Avoid clipboard clearance claims and network fallbacks.

Expose min and max length, minimum entropy, and the capitalize-first-letter
option that `SPEC.md` defines. Punctuation and digits are fixed by `SPEC.md`.
Do not add controls for them. Add a restrictive-site preset that turns on
capitalization. Match `python/passphrase.py --capitalize` in the parity tests. Keep settings
in page memory. Discard generated values on reload. Place no secret in
storage, cookies, URLs, diagnostics, telemetry, or caches.

Pin Playwright and the other browser test dependencies in
`tests/browser/`. Use them only for verification. The gate needs Node.js,
npm, Chromium system libraries, and access to the pinned test tooling or
its cache. Test controlled parity with the Python vectors, including
unbiased rejection and error paths. Test keyboard use, accessibility
semantics, copy and reveal behavior, responsive layouts, and reload.
Check screen-reader behavior and record the environment. Intercept
requests during generation and copy after initial asset load. Check URLs,
cookies, local storage, session storage, logs, and caches for secret values.
Use fixtures that keep assertion output free of real secrets.
Record gate evidence in this step.

## Resume notes

Gate environment: Linux (WSL2), Node.js 24, Playwright 1.65.1, Chromium 159 headless. The tests check the accessibility tree (roles, names, states, live regions). No real screen reader (NVDA, VoiceOver, TalkBack) ran. A person must test one on a real device in step 05. The app loads the word list with fetch, so it needs an HTTP origin. Step 04 must handle file or offline packaging.
