---
id: 04b-symbol-set
status: pending
depends_on: [04a-single-file-release]
touches:
  - SPEC.md
  - SECURITY.md
  - docs/feasibility.md
  - docs/release.md
  - README.md
  - python/**
  - tests/test_generator.py
  - tests/fixtures/**
  - web/**
  - tests/browser/**
  - plans/build-passphrase-deck/plan.md
  - plans/build-passphrase-deck/steps/04b-symbol-set.md
  - plans/build-passphrase-deck/steps/05-production-verification.md
lane: none
gate: python3 scripts/verify_wordlist.py && python3 -m unittest discover -s tests -p 'test_*.py' && python3 scripts/check_feasibility.py && (cd tests/browser && npm ci && npx --no-install playwright install chromium && npm test) && python3 scripts/verify_release.py --self-test && python3 scripts/check_context.py && git diff --check
evidence: ""
---

# Let the user choose the separator symbols

Decision (owner, 2026-11-24): the symbol between words is no longer always
an underscore. The user can edit the set of allowed symbols. Sites have
their own odd rules, so the set must be easy to change.

## Design

**The symbol set.** The set is a string of distinct symbols. The default
is `.,#$_!?` in that order. Accept 1 to 32 symbols. Each symbol must be a
printable ASCII punctuation character. Reject letters, digits, space,
hyphen, control characters and non-ASCII characters. Reject a repeated
symbol. A word can contain a hyphen, so a hyphen would make the output
ambiguous. Reject the whole policy on any bad symbol. Never drop a symbol
silently. Report the symbol that failed, as a character name or position,
not by echoing a secret.

**Where symbols go.** Each of the `count - 1` gaps between words gets one
symbol. Each gap is independent. The readable value is the word, the
symbol and one space, for each gap. The last word has the digits appended
as before. The compact value removes only ASCII spaces. Lengths do not
change, because a symbol is one character, the same as the old underscore.
All length checks and the completion counts stay as they are.

**Entropy.** The symbols now add entropy. The output count is the valid
word tuples, times 10 to the digit count, times the symbol count raised to
`count - 1`. Use that count for the scheme choice and for the entropy
floor. Keep the scheme order (4 words, then 6 words). A set of one symbol
must give the old output counts exactly. The symbol set is not a secret.

**Rank layout.** Keep the old layout and add the symbols in the middle.
Take the remainder of the rank by 10 to the digit count for the digits.
Divide, then take the remainder by the symbol count for each gap symbol, with
the first gap as the most significant of the symbol digits. The quotient is
the tuple rank as before. With one symbol the symbol part is zero, so the
old vectors stay valid. Both runtimes must use this layout and the same
unbiased random draw as before.

**Interfaces.** The Python CLI gets `--symbols STRING` with the default
set. The web app gets one text field, labelled for people, with the
default value, and a reset-to-default control. Keep it in page memory
only. Show an accessible error for a bad set and keep the last good
policy. Never use `innerHTML` for symbols. Check that a symbol such as `<`,
`&` or a quote is shown as text. The restrictive-site preset keeps its
capitalization setting and does not change the set.

## Work

1. Update `SPEC.md` first. Replace the fixed-underscore text. Record this
   decision there. Update `docs/feasibility.md` and `SECURITY.md` where they
   say separators add no entropy. Keep `scripts/check_feasibility.py` as it
   is. It measures lengths, and lengths do not change.
2. Update `python/passphrase.py` and its tests. Add public controlled
   vectors for a multi-symbol set to `tests/fixtures/`. Keep the old
   one-symbol (`_`) vectors and show they still pass.
3. Update `web/` with the same logic and the new field. Add browser
   parity tests against the Python vectors, plus tests for bad sets, the
   reset control, keyboard use, and symbols that look like markup.
4. Check that the one-file build still passes `verify_release.py`.
   Do not change the CSP rules or the `data-cfasync` attribute.
5. Update `README.md` and `docs/release.md` if they mention the underscore.

## Resume notes

Done and checked (gate parts that ran): `verify_wordlist.py`, the Python unit
tests, `check_feasibility.py`, `verify_release.py --self-test`,
`check_context.py`.

Done but NOT run: the browser part of the gate. The shell in the first session
denied `npm`, `npx` and `node`. These files changed and need a run of
`cd tests/browser && npm ci && npx --no-install playwright install chromium && npm test`:
`web/core.js`, `web/app.js`, `web/index.html`, `tests/browser/app.spec.js`,
`tests/browser/core.spec.js`, `tests/browser/single.spec.js`,
`tests/browser/offline.spec.js`.

Next agent: run the browser gate. Fix any failure. Likely risks: the new
`#symbols-error` alert and `getByRole('alert')` strict mode in `app.spec.js`;
the `settings input` count (now 5). Then run `git diff --check`, set
`status: done`, record `evidence`, and commit.

## Limits

Do not change the wordlist, the schemes, or the length rules. Do not deploy.
Do not log or record any real generated passphrase. Record the gate result.
