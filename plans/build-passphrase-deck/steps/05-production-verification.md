---
id: 05-production-verification
status: pending
depends_on: [04-offline-release, 04a-single-file-release]
touches:
  - docs/release-evidence.json
  - docs/README.md
  - plans/build-passphrase-deck/steps/05-production-verification.md
lane: none
gate: python3 scripts/verify_release.py --production https://dullroar.com/passphrase.html --evidence docs/release-evidence.json && python3 scripts/check_context.py && git diff --check
evidence: ""
---

# Verify the reviewed release on the production host

Start after the [operator handoff](../plan.md#operator-handoff-before-step-05).
Use sanitized operator evidence in `docs/release-evidence.json`. It must
identify the candidate revision and checksums, independent review date
and disposition, real iOS Safari and Android Chrome results, offline
mode and installation behavior, and the deployed artifact. Associate
all results with the same candidate. Use roles or approved references for
reviewers. Keep credentials, personal information, and generated values out
of the record.

Run the read-only production verifier prepared in step 04. It must fail
on missing evidence, unresolved findings, failed device checks, a TLS
failure, missing required response headers, external runtime origins, or
an asset mismatch. Verify the actual hosted bytes against the reviewed
release manifest and test that generation and copy issue no network
requests after asset load. Document any platform limits and the
verified offline path. Changes to the candidate go back through the
affected gates and review before deployment.

Record the exact command, result, date, revision, and release checksums.
When review, real phone checks, publication authorization, or production
verification is missing, record what is needed and keep the gate open.
