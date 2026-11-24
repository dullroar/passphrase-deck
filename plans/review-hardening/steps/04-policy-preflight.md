---
id: 04-policy-preflight
status: done
depends_on: [03-secret-lifecycle]
touches:
  - SPEC.md
  - README.md
  - python/**
  - web/**
  - tests/**
  - plans/review-hardening/steps/04-policy-preflight.md
lane: none
gate: python3 scripts/verify_wordlist.py && python3 -m unittest discover -s tests -p 'test_*.py' && python3 scripts/check_feasibility.py && (cd tests/browser && npm ci && npx --no-install playwright install chromium && npm test) && python3 scripts/verify_release.py --self-test && python3 scripts/check_context.py && git diff --check
claimed_by: ""
claimed_at: ""
evidence: gate passed 2026-11-24 (full gate command; 36 Python tests, 74 browser tests, release self-test, context checks)
---

# Show policy status before a deal

Policy checks are deterministic. They need no randomness and hold no secret.
Today the user learns of an unsupported policy only after pressing Deal.

## Change

- Expose one pure function in `web/core.js` and `python/passphrase.py`. It
  takes the settings and returns one of three states: malformed, unsupported,
  or valid. For valid, it returns the scheme and the exact bit count. For the
  other two, it returns the existing error code and message. Reuse the
  existing validation and `selectPolicy`. Do not copy their logic.
- In the page, run it on every setting change and show the state in an
  element that screen readers announce politely. Name the state in words,
  not by color only. For unsupported, keep the existing advice to raise the
  maximum or lower the target. Disable Deal when the state is not valid.
- The preflight must not call the random source. Add a test for that.
- Add parity tests between Python and JavaScript on a table of settings.
  Add browser tests for each of the three states.
- Describe preflight in `SPEC.md`.

## Do not change

- The policy rules, the error codes, the scheme order.

## Done when

- A change to any setting updates the status without a deal.
- Deal cannot run on a malformed or unsupported policy.

## Record

Set `status: done`. Fill `evidence` with the gate command, the result and the date.

## Resume notes

(none)
