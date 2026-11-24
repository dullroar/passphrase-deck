---
id: 01-exhaustive-rank-tests
status: done
depends_on: []
touches:
  - tests/**
  - python/**
  - web/core.js
  - plans/review-hardening/steps/01-exhaustive-rank-tests.md
lane: none
gate: python3 scripts/verify_wordlist.py && python3 -m unittest discover -s tests -p 'test_*.py' && python3 scripts/check_feasibility.py && (cd tests/browser && npm ci && npx --no-install playwright install chromium && npm test) && python3 scripts/verify_release.py --self-test && python3 scripts/check_context.py && git diff --check
claimed_by: claude cli-default
claimed_at: "2026-11-24T15:50:53Z"
evidence: gate passed 2026-11-24 (driver-verified)
---

# Prove the rank mapping with an exhaustive test on a tiny dictionary

The output is a bijection from integer ranks to valid outputs. Test that fact
directly. Do not use statistical tests. Do not use the optimized counting code
to check itself.

## Change

- Add a brute-force reference in the tests. It builds all word tuples, symbol
  choices and digit strings from a tiny synthetic dictionary and a small
  policy, then filters them by the length rules. It shares no code with the
  dynamic-programming counter.
- For every rank, in Python and in the browser core, check:
  - The total count equals the brute-force count.
  - All readable outputs are distinct. All compact outputs are distinct.
  - Each output meets the length rules.
  - Each output splits back to its words, symbols and digits.
  - Python and JavaScript give the same output. Share the results through a
    public fixture file, not through live generation.
- Check that length limits remove exactly the expected outputs.
- Check that capitalization keeps the count and the distinctness.
- Check the random draw at its boundaries: the largest accepted value, the
  first rejected value, and `RANDOM_LIMIT` after 128 draws. A failure returns
  no secret.
- Repeat with several generated tiny dictionaries and policies. Use a fixed seed.

## Do not change

- The wordlist, the schemes, the length rules, the rank layout and the gate.
- If a test finds a bug, make the smallest fix and write it in "Resume notes".

## Done when

- The new tests pass in both runtimes. They fail if a rank or a length rule is changed on purpose.

## Record

Set `status: done`. Fill `evidence` with the gate command, the result and the date.

## Resume notes

No bug found. New files: `tests/test_exhaustive.py`, `tests/browser/exhaustive.spec.js`,
`tests/fixtures/exhaustive.json`. To rewrite the fixture, run the Python test with `UPDATE_EXHAUSTIVE=1`.
