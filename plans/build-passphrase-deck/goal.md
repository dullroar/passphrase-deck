# Build Passphrase Deck

## Ralph loop prompt

> Read `AGENTS.md`, this file, [plan.md](./plan.md), and the assigned step.
> Work in the assigned worktree and branch. Change only files in the step's
> `touches`. Follow the accepted design and preserve all earlier gates.
> Run the step's `gate`. Record the command, date, and result in the step and
> commit the work. Keep resumable notes for unfinished work. When a required
> decision or verification is missing, record the blocker and its evidence.
> Use public test fixtures and controlled random streams for examples. Keep
> actual generated passphrases out of logs, prompts, and evidence. The operator
> controls deployment, public distribution, and approvals.

## Goal

Build a small, auditable passphrase generator for desktop and phone. A deal
returns one English-word passphrase in two formats. The browser and Python
reference use the same wordlist, policy, and formatting specification.

## Done when

- The pinned wordlist and feasible default policy pass the design gate. The
  entropy bound applies to the output users can copy.
- The Python CLI, static browser app, and verified offline release pass
  their gates. Both variants meet the selected policy.
- The independent security review, real phone checks, and production
  verification are recorded for the released artifact.
- Every step is `done` with gate evidence. Escalations remain open until the
  required decision or verification is recorded.

## Launch from a checkout containing this plan

Use Claude through the installed runner. Start with the design step to review
the measured feasible configurations and selected policy before coding.

```bash
ralph-looper --repo "$PWD" --plan build-passphrase-deck \
  --agent claude --jobs 1 --max-iterations 1 --on-limit handoff
```

Run this command from the repository root. It can exit at the iteration
limit after a successful step. Check the committed step state on
`plan/build-passphrase-deck` before proceeding. After design review, use
`--max-iterations 3` for steps 02 through 04 when 01 is the only completed
step. If resuming partway through, set the limit to the number of remaining
steps through 04. Wait for the operator handoff in the
[plan](./plan.md#operator-handoff-before-step-05) before starting step 05.
