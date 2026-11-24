---
id: 01-specification
status: done
depends_on: []
touches:
  - SPEC.md
  - SECURITY.md
  - data/**
  - docs/feasibility.md
  - docs/README.md
  - scripts/verify_wordlist.py
  - scripts/check_feasibility.py
  - scripts/AGENTS.md
  - plans/build-passphrase-deck/steps/01-specification.md
lane: none
gate: python3 scripts/verify_wordlist.py && python3 scripts/check_feasibility.py && python3 scripts/check_context.py && git diff --check
evidence: "2026-11-23: full gate passed after approved separator correction; see evidence below."
---

# Specify the generator and prove the feasible policies

Pin the wordlist in `data/`. Record its source, revision or retrieval date,
license or redistribution terms, required attribution, SHA-256, count,
encoding, and accepted character set. Prefer the 7,776-word EFF long list.
Verify the digest independently of the file content. Fail closed on an
incorrect hash, count, encoding, duplicate, empty entry, or invalid character.

Write `SPEC.md` for both runtimes. Define fragments and their exact order,
word-count selection, capitalization, punctuation and digit placement,
allowed ASCII characters, and policy errors. Define length counting for
both variants and bound all retries. Specify how preflight handles impossible
policies and how the runtime responds if an attempt limit is reached.
Use Python `secrets.token_bytes()` and browser `crypto.getRandomValues()` with
unbiased integer rejection sampling. For a range of size n, reject draws
at or above the largest multiple of n within the source range before
reducing modulo n. Keep test random sources out of the production interface. Document that the deterministic parts are the build,
tests, and formatting rules. Each deal draws new randomness.

In `docs/feasibility.md`, report the actual word-length distribution. Use
`scripts/check_feasibility.py` to reproduce the analysis, exercise at least
one impossible policy, and verify both the chosen initial policy outcome and
a feasible 80-bit policy. A full-list independent draw has about 51.7 bits
for four words, 64.6 for five, and 77.5 for six before any independent,
observable embellishment. Check the actual output distribution after
policy enforcement, including conditioning on successful generation,
scheme selection, and collisions in the compact representation. Bound the
maximum probability of a copyable value in each format. Use a uniform
feasible set with proven distinct outputs or justify a conservative bound
for the actual distribution. Include a small exhaustive test that detects
bias or collisions in the calculation. Fixed formatting and removal of
spaces contribute zero bits.

Test the 12–32 request with both length bounds applied to both formats.
If the design cannot meet that request at 64 bits, specify an explicit
error and a measured feasible adjustment. Record the tradeoffs of a
longer maximum, an independently audited short-word list, and additional
independent symbols or digits where relevant. Ask the owner to decide
when the default range or wordlist must change. Keep the entropy floor.

Write `SECURITY.md` with the threat model and vulnerability reporting
instructions. Cover compromised hosting, script injection, dependencies,
browser extensions, clipboard readers, phishing, and device compromise.
Document the trust users place in served or updated code and the offline
alternative. Review the threat model against the specification and record
the result. Update the docs and script indexes.

Record the exact gate, date, results, the selected default behavior, and
any decision still needed. Both the reproducible analysis and the written
entropy argument must support the recommended policy.

## Evidence and resume notes

- On 2026-11-23, the prescribed Ralph launch selected this step. Its Claude
  attempt produced no output or file changes before it was interrupted.
  The owner then directed Codex to perform the work.
- On 2026-11-23, the complete gate passed with exit code 0:
  `python3 scripts/verify_wordlist.py && python3 scripts/check_feasibility.py && python3 scripts/check_context.py && git diff --check`.
- The selected default is 12–32 characters, at least 64 bits, four words,
  and six independent decimal digits. Both formats have about 64.994089
  bits of min-entropy under the specified sampler. The 12–48, 80-bit policy
  also passed. See [the analysis](../../../../../docs/feasibility.md).
- The requested range and wordlist are unchanged. No owner decision is
  required by this step. Review the six-digit tradeoff before coding. If
  the design changes, update the analysis and specification and rerun the
  full gate.

## Approved correction

On 2026-11-23, the owner approved replacing `secrets.randbelow()` with
`secrets.token_bytes()` and bounded rejection. The former can retry inside
Python without a caller-visible bound. The correction retains OS randomness
and makes the 128-draw limit enforceable. The full gate was rerun.

## Feasibility correction needed

On 2026-11-23, step 02 boundary tests showed that the analysis counts
` _ ` as two characters although it has three. The earlier gate passed but
does not prove the stated entropy. Corrected counts give approximately
60.521378 bits for the 12–32 default and 76.175629 bits for 12–48 with
the specified schemes. The default must not be used under the stated
64-bit floor. Select a revised format or policy, correct the analysis and
tests, and rerun this gate. Step 02 records the evidence and alternatives.

## Approved separator correction

On 2026-11-23, the owner agreed to use `_ ` as the readable separator.
It has two characters and becomes `_` in the compact format. The prior
12–32 and 12–48 counts now match the specified format. The exhaustive
fixture checks formatted string lengths directly. The full gate passed:
`python3 scripts/verify_wordlist.py && python3 scripts/check_feasibility.py && python3 scripts/check_context.py && git diff --check`.
