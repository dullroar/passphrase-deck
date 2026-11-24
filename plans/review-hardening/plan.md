---
gist: "Read me when: you work on the hardening that follows the external review of Passphrase Deck (symbol limit, secret lifecycle, preflight, exhaustive tests, delivered artifact)."
---

# Review hardening

## Approach

The reviewer found the core algorithm sound. The findings sit at the edges.
Each step is one finding, with the facts the agent cannot find itself.
Steps run in order. Most steps touch `SPEC.md`, so they do not run in parallel.

Step 01 comes first. It adds a brute-force reference and an exhaustive rank
test. Later steps change code. This test then guards the core.

Review findings that this plan does not adopt:

- More schemes: a feature decision, not a defect. The spec is explicit.
- Excluding hyphenated words: the owner decided against it. A hyphen can act
  as a space. The wordlist pool stays whole.
- Banning the hyphen as a symbol: the owner decided to allow it unless it
  lowers entropy. Step 02 measures that.
- Cloudflare injection: already handled by `data-cfasync` and the production
  verifier. Step 05 closes the remaining gap.

## Steps

| Step | Goal | Depends on |
| --- | --- | --- |
| [01-exhaustive-rank-tests](steps/01-exhaustive-rank-tests.md) | Prove the rank mapping on a tiny dictionary against a brute-force reference. | none |
| [02-symbol-limit-and-reject](steps/02-symbol-limit-and-reject.md) | Settle the hyphen as a symbol and the symbol limit. A bad symbol set stops the deal. | 01 |
| [03-secret-lifecycle](steps/03-secret-lifecycle.md) | Specify and test when a secret ends. Add the cherry-pick notice. | 02 |
| [04-policy-preflight](steps/04-policy-preflight.md) | Show policy status before a deal. | 03 |
| [05-delivered-artifact](steps/05-delivered-artifact.md) | Specify the delivered artifact. Make the digest check mandatory. | 04 |

## Parallelism

None. The steps share `SPEC.md` and the core files.

## Risks

- Step 01 can find a real bug. Fix it in the step, record it, and keep the test.
- Step 05 changes the production verifier flags. Update the old step 05 gate in
  `build-passphrase-deck` in the same step, or that gate fails.
