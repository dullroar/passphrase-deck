---
gist: "Read me when: you need to build, verify, or release the Passphrase Deck browser app and Python reference."
---

# Build Passphrase Deck

## Approach

Use plain HTML, CSS, JavaScript, and the Python standard library. Use one
pinned wordlist as the source for both implementations. Start with the
[EFF long list](https://www.eff.org/dice). Package it with the application so
generation works without network access. Verify provenance, redistribution
terms, and the content hash before use.

Each deal starts with fresh OS or browser cryptographic randomness. The
readable format uses English words with the selected capital, punctuation,
and digit options. The compact format removes only ASCII spaces. Select
from a feasible scheme with an auditable bound on output entropy. Test with
controlled random choices. Use the actual CSPRNG in production.

Use an initial requested length range of 12–32 ASCII characters and a minimum
of 64 bits. Both formats must meet both bounds. Support longer maxima and
entropy targets of 80 bits or higher. Step 01 measures feasibility before
the defaults are locked. Preserve the entropy floor. If the initial request
cannot be met, show the conflict and suggest a feasible change. A change
to the published default range or use of a separate wordlist needs a
recorded design decision.

Use a static site and a versioned offline download. Add a PWA only if it
solves a concrete phone-use problem. Keep the private repository and
product source distribution under the owner's control.

## Steps

| Step | Goal | Depends on |
| --- | --- | --- |
| [01-specification](steps/01-specification.md) | Verify the wordlist, modeling assumptions, and feasible policies. | None |
| [02-python-reference](steps/02-python-reference.md) | Implement and test the reference CLI. | 01 |
| [03-static-web](steps/03-static-web.md) | Implement the responsive app and verify browser isolation and parity. | 02 |
| [04-offline-release](steps/04-offline-release.md) | Package and verify the offline release and prepare release instructions. | 03 |
| [04a-single-file-release](steps/04a-single-file-release.md) | Build one self-contained `passphrase.html` with hash-based CSP. | 04 |
| [04b-symbol-set](steps/04b-symbol-set.md) | Let the user choose the separator symbols. | 04a |
| [05-production-verification](steps/05-production-verification.md) | Verify the reviewed release on the production host and record acceptance evidence. | 04b and operator handoff |

The steps run in order. Later steps use the accepted specification, reference
fixtures, or release artifact from earlier steps.

## Operator handoff before step 05

Use the [launch instructions](goal.md#launch-from-a-checkout-containing-this-plan)
to stop after the design and again after offline release preparation.
Escalate a wordlist rights question, an unsupported entropy claim, or a
default policy conflict that needs the owner's decision. Leave the relevant
gate open when an issue affects its result.

After step 04, give an independent reviewer the exact release candidate and
checksums. Resolve findings and rerun affected gates before deployment.
Record real-device results for iOS Safari and Android Chrome, including
offline use and installation or home-screen behavior where offered. Record
the mode tested and any operating-system limitations. Emulator results can
supplement the real-device checks.

After review, the owner authorizes and performs or delegates deployment to
`https://dullroar.com/passphrase.html`. The owner also decides which source files
and versioned artifacts may be published under the proprietary license and
the wordlist's terms. Supply the sanitized review, phone, and deployment
evidence to Claude outside the repository. Start step 05 only after those
inputs and the production site are available. Keep the gate open if the
review, devices, or deployed revision cannot be verified.

## Scope limits

The scope is one local deal at a time, plus explicit CLI batch output. It
excludes accounts, sync, password history or reuse tracking, password vaults,
master seeds, recovery, online dictionaries, LLM-generated secrets, and hosted
password-manager integration. Describe strength using the generation model
and accepted policy.
