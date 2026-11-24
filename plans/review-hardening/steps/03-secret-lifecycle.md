---
id: 03-secret-lifecycle
status: pending
depends_on: [02-symbol-limit-and-reject]
touches:
  - SPEC.md
  - SECURITY.md
  - README.md
  - web/**
  - tests/browser/**
  - plans/review-hardening/steps/03-secret-lifecycle.md
lane: none
gate: python3 scripts/verify_wordlist.py && python3 -m unittest discover -s tests -p 'test_*.py' && python3 scripts/check_feasibility.py && (cd tests/browser && npm ci && npx --no-install playwright install chromium && npm test) && python3 scripts/verify_release.py --self-test && python3 scripts/check_context.py && git diff --check
claimed_by: ""
claimed_at: ""
evidence: ""
---

# Specify and test when a secret ends

The spec says how a secret is made. It does not say when it must end. Add
that, and make the page follow it.

## Change

- Add a "Secret lifecycle" section to `SPEC.md`. For each event, say what
  happens to the page's references to the secret:
  - Any change to a generation setting: clear.
  - An invalid setting: clear, and do not deal.
  - A new deal: clear the old one first.
  - A failed deal: leave no secret.
  - The tab becomes hidden: clear.
  - Leaving the page and coming back through the back/forward cache
    (`pagehide`, `pageshow` with `persisted`): clear.
  - Copy: the page does not clear the clipboard. A copy failure keeps the
    secret and says so.
  - Logs, errors and telemetry never hold a secret. Error text never
    includes one.
- State that dropping references is best-effort disposal. It is not secure
  memory erasure. Say the same in `SECURITY.md`.
- Implement each rule in `web/app.js`. Keep the existing Hide control.
- Add one notice near the result: the entropy bound covers the generated
  passphrase only. Choosing a result by its content, or editing it, lowers
  the strength. Put the figures in `docs/feasibility.md` or `SECURITY.md`:
  if a user accepts one deal in N, the loss is log2(N) bits.
- Add browser tests for each event above, including a simulated hidden tab
  and a `pageshow` with `persisted` true. Use controlled data.

## Do not change

- The random draw, the formats, the CSP, `data-cfasync`.
- Do not add storage, a clipboard timer, or any network call.

## Done when

- `SPEC.md` lists every event above. A browser test covers each one.

## Record

Set `status: done`. Fill `evidence` with the gate command, the result and the date.

## Resume notes

(none)
