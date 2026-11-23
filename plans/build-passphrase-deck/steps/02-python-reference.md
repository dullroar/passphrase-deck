---
id: 02-python-reference
status: pending
depends_on: [01-specification]
touches:
  - python/**
  - tests/test_generator.py
  - tests/fixtures/**
  - plans/build-passphrase-deck/steps/02-python-reference.md
lane: none
gate: python3 scripts/verify_wordlist.py && python3 -m unittest discover -s tests -p 'test_*.py' && python3 scripts/check_context.py && git diff --check
evidence: ""
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
