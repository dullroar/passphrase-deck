---
id: 01-specification
status: pending
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
evidence: ""
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
Use Python `secrets.randbelow()` and browser `crypto.getRandomValues()` with
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
