---
id: 05-delivered-artifact
status: done
depends_on: [04-policy-preflight]
touches:
  - SPEC.md
  - SECURITY.md
  - docs/release.md
  - scripts/verify_release.py
  - tests/test_release.py
  - plans/build-passphrase-deck/steps/05-production-verification.md
  - plans/review-hardening/steps/05-delivered-artifact.md
lane: none
gate: python3 scripts/verify_wordlist.py && python3 -m unittest discover -s tests -p 'test_*.py' && python3 scripts/check_feasibility.py && (cd tests/browser && npm ci && npx --no-install playwright install chromium && npm test) && python3 scripts/verify_release.py --self-test && python3 scripts/check_context.py && git diff --check
claimed_by: claude cli-default
claimed_at: "2026-11-24T16:01:18Z"
evidence: gate passed 2026-11-24 (driver-verified)
---

# Specify the delivered artifact and make the digest check mandatory

The user trusts the page the host delivers, not the repository. A host can
change the bytes, as an edge proxy that injects a script does. Today
`--production` accepts `--manifest` as optional, so the digest check can be
skipped.

## Change

- Add a "Delivered artifact" section to `SPEC.md`. The delivered page:
  has no external executable resource; makes no network request from the
  application; has no analytics or telemetry; has a restrictive CSP; works
  offline; and matches a published release digest byte for byte.
- Make `--manifest` required for `--production` in `scripts/verify_release.py`.
  Fail with a clear message when it is missing. Update the usage text and the
  self-test. Add a test that production mode refuses to run without it.
- The verifier already checks bytes, CSP, headers and external origins. Check
  each item in the new spec section against it. Add a check, with a self-test,
  for any item that no check covers. Keep the verifier read-only.
- Update the `gate` of step 05 in `plans/build-passphrase-deck/steps/05-production-verification.md`
  to pass `--manifest` with the manifest path from `docs/release.md`. Change
  nothing else in that step.
- Update `docs/release.md`.

## Do not change

- The CSP rules, `data-cfasync`, the package build. Do not deploy.

## Done when

- `verify_release.py --production URL --evidence F` without `--manifest` fails.
- Each requirement in the new spec section maps to a check or a recorded reason.

## Record

Set `status: done`. Fill `evidence` with the gate command, the result and the date.

## Resume notes

(none)
