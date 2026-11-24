---
id: 02-symbol-limit-and-reject
status: done
depends_on: [01-exhaustive-rank-tests]
touches:
  - SPEC.md
  - SECURITY.md
  - README.md
  - docs/**
  - python/**
  - web/**
  - tests/**
  - plans/review-hardening/steps/02-symbol-limit-and-reject.md
lane: none
gate: python3 scripts/verify_wordlist.py && python3 -m unittest discover -s tests -p 'test_*.py' && python3 scripts/check_feasibility.py && (cd tests/browser && npm ci && npx --no-install playwright install chromium && npm test) && python3 scripts/verify_release.py --self-test && python3 scripts/check_context.py && git diff --check
claimed_by: ""
claimed_at: ""
evidence: "2026-11-24: the gate passed (31 Python tests, 57 browser tests, feasibility, release self-test, context check). The hyphen is safe: the four hyphenated list words do not split into list words (drop, felt, tip, t and yo are not list words). The Sardinas-Patterson test in tests/test_hyphen.py proves it. The hyphen is allowed and the limit stays 32."
---

# Settle the hyphen and the symbol limit, and stop the deal on a bad set

Decision (owner, 2026-11-24): do not ban the hyphen as a separator unless
that lowers entropy or weakens the output in some other way. A hyphen can
work as a space between two words. Do not exclude hyphenated words either.

Today the set bans the hyphen and allows up to 32 symbols. ASCII has 32
punctuation characters. With the hyphen banned, the real limit is 31, so a
set of 32 can never be valid. The two rules do not agree. Fix that.

Second defect: the page keeps the last good set when the field is bad. It
then deals with a set that the field does not show. This weakens the policy
without notice and breaks "Never silently weaken the policy".

## Change

- First, test whether a hyphen symbol hurts. The compact format removes the
  spaces. A hyphen gap and a hyphen inside a word (`drop-down`, `felt-tip`,
  `t-shirt`, `yo-yo`) must not make two different outputs equal. Write a
  script or test that proves the compact value decodes in only one way, for
  the real wordlist, every scheme and a symbol set that holds the hyphen.
  Include the digits at the end. Check by an exact method, not by sampling.
  It is also fine to check the four words against the list by hand, and then
  test the general case with brute force on small synthetic lists.
- If the hyphen is safe: allow it. The symbol limit stays 32. Remove the
  hyphen ban and its reason in `SPEC.md`, `python/passphrase.py`,
  `web/core.js`, the CLI help, the page text, the docs and the tests. Keep
  the default set. Keep the decodability proof as a permanent test.
- If the hyphen is not safe: keep the ban. Write the colliding example in
  `SPEC.md`. Change the limit to 31 everywhere. Add a test that 32 is
  rejected for the count.
- Either way, the written limit must equal the number of allowed
  characters, and a test must accept a set of that size.
- A bad set in the page stops the deal. Show the error. Show no new
  passphrase. Clear any shown secret. Remove the "last good set" variable and
  its message. Keep the accessible error and `aria-invalid`.
- Add browser tests: a bad set, then Deal, gives an error and no output.
  After the fix, the next deal works.

## Do not change

- The rank layout, the default set, the schemes, the CSP, `data-cfasync`.

## Done when

- The symbol rules, the limit and the proof agree in `SPEC.md`, code and tests.
- The page never deals with a set that differs from the field.

## Record

Set `status: done`. Fill `evidence` with the gate command, the result and the date.

## Resume notes

(none) The step is done.
