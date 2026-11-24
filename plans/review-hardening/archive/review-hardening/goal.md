# Review hardening

## Ralph loop prompt

> Read `AGENTS.md`, this file, [plan.md](./plan.md), and the assigned step.
> Work in the assigned worktree and branch. Change only files in the step's
> `touches`. Preserve all earlier gates and the wordlist, the schemes and the
> length rules. Run the step's `gate`. Do not weaken or delete the gate.
> Record the command, date and result in the step, then commit. If you cannot
> finish, keep `status: in_progress` and write "Resume notes". If you are
> blocked, set `status: blocked` and write the reason. Use public test
> fixtures and controlled random streams. Keep real generated passphrases out
> of chat, logs, prompts and evidence. Do not deploy. Write in Simplified
> Technical English.

## Goal

Fix the findings of an external review of the specification and code of
Passphrase Deck. The core algorithm stays as it is. The work covers the
boundaries: the symbol-set limit, invalid settings, the life of a secret in
the page, early feedback on unsupported policies, proof of the rank mapping by
exhaustive test, and the delivered artifact on the production host.

## Done when

- A tiny synthetic dictionary gives a full rank-to-output test in both runtimes.
  It agrees with a brute-force reference.
- The hyphen is allowed as a symbol if a proof shows it adds no ambiguity. The symbol limit matches the allowed characters. A bad set stops the deal. No old set is used.
- `SPEC.md` has a secret lifecycle section and a delivered-artifact section.
  The page follows the lifecycle rules, and tests prove it.
- The page shows policy status before a deal, without randomness.
- Production verification needs the release manifest. It cannot skip the digest check.
- Every step is `done` with gate evidence.

## Out of scope

- More generation schemes. The two fixed schemes stay.
- Any change to the wordlist file, the length rules or the random draw rule.
- Deployment. The owner does that.
