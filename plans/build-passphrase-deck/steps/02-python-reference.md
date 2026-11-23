---
id: 02-python-reference
status: done
depends_on: [01-specification]
touches:
  - python/**
  - tests/test_generator.py
  - tests/fixtures/**
  - plans/build-passphrase-deck/steps/02-python-reference.md
lane: none
gate: python3 scripts/verify_wordlist.py && python3 -m unittest discover -s tests -p 'test_*.py' && python3 scripts/check_context.py && git diff --check
evidence: "2026-11-23: full gate passed after approved design corrections; see completion evidence."
---

# Implement the standard-library Python reference

Implement `python/passphrase.py` with the pinned wordlist and accepted
policy in `SPEC.md`. Validate the wordlist before generation. Generate one
pair by default. Support length and entropy options and explicit opt-in
batch output with `--count`.

```sh
python3 python/passphrase.py --min 12 --max 32
python3 python/passphrase.py --min 20 --max 40 --entropy 80
python3 python/passphrase.py --count 10
```

Document how stdout, terminal scrollback, shell capture, and the clipboard
can expose secrets. Print only the requested output to stdout. Keep errors
free of secret values. Leave file writes and persistence out of the CLI.

Test length boundaries, allowed characters and controls, impossible
policies, bounded retries, wordlist validation, unbiased selection and
rejection, and exact removal of ASCII spaces. Test the specified entropy
calculation with controlled choices and small exhaustive cases. Verify
fresh production calls use the CSPRNG and do not share test state. Commit
shared deterministic vectors for the browser parity check. Use synthetic
inputs and keep generated values out of runner and CI output. Record gate
evidence in this step.

## Resume notes

- The step 01 commit is on the plan branch. Its complete gate passed again
  on 2026-11-23.
- The step 02 gate was run on 2026-11-23:
  `python3 scripts/verify_wordlist.py && python3 -m unittest discover -s tests -p 'test_*.py' && python3 scripts/check_context.py && git diff --check`.
  Wordlist verification passed. The test command failed with exit code 1:
  `ImportError: Start directory is not importable: 'tests'`. The test
  directory and implementation do not exist yet. Later commands did not run.
- Design blocker: `SPEC.md` requires Python `secrets.randbelow(n)` and a
  limit of 128 random rejection draws. The installed Python implementation
  calls `SystemRandom._randbelow`, which retries internally in an unbounded
  `while r >= n` loop. The caller cannot enforce the specified draw limit
  with that interface. No reference implementation is complete.
- Proposed resolution: revise the specification to use `secrets.token_bytes`
  with the specified 128-attempt rejection algorithm, then rerun the step 01
  gate and implement step 02. The specification is outside this step's
  `touches`; obtain a decision and authorization for that change first.

## Feasibility blocker after random-source correction

- On 2026-11-23, the owner approved bounded sampling from
  `secrets.token_bytes()`. The correction was committed on the step 01 branch
  and its full gate passed. The corrected commit is on the plan branch.
- The controlled boundary tests found that the step 01 calculation counts
  two readable characters per separator. The specification uses ` _ `,
  which has three. For four words, six digits, and 12–32 characters,
  the corrected count is 1,654,817,711,489 word tuples and approximately
  60.521378 bits. For six words, two digits, and 12–48 characters, the
  corrected result is approximately 76.175629 bits. The earlier gate
  passed but did not detect this error. Its entropy claims are not valid.
- The corrected Python length calculation rejects the specified default
  policy rather than generating below its floor. The step 02 gate was run
  again on 2026-11-23 using the command above. Wordlist verification passed.
  The tests failed with exit code 1: one failure and two errors, all due to
  the unsupported default. The remaining gate commands did not run.
- The implementation and controlled tests are incomplete. Preserve them
  for resumption. Do not mark either design or implementation verified
  until the specification, feasibility analysis, and tests agree.
- A possible adjustment is to use `_ ` as the readable separator. It has
  two characters and remains `_` after spaces are removed. This preserves
  the existing count and requested bounds but changes the visible format.
  Another adjustment is a maximum of 35 with the present separator; that
  changes the default range and needs the owner's decision. Review the
  alternatives, revise step 01 within its permitted files, rerun its gate,
  then update this implementation and rerun the step 02 gate.

## Completion evidence

- On 2026-11-23, the owner agreed to the `_ ` readable separator. Step 01
  was corrected and its complete gate passed. The corrected design is on
  the plan branch and included in this step branch.
- The reference uses bounded rejection with `secrets.token_bytes`, exact
  integer counts, and deterministic unranking. Shared vectors use public
  synthetic words and controlled ranks. The tests check formatted lengths
  at rank boundaries and exhaustively check a small fixture.
- On 2026-11-23, this full gate passed with exit code 0:
  `python3 scripts/verify_wordlist.py && python3 -m unittest discover -s tests -p 'test_*.py' && python3 scripts/check_context.py && git diff --check`.
