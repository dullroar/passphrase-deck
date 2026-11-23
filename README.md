# Passphrase Deck

Passphrase Deck is planned as a small passphrase generator for desktop and
phone. Each deal creates one secret in two formats. The readable version has
spaces. The compact version removes those ASCII spaces and keeps every
other character. Copy the format the destination accepts and save that format
in your password manager. Treat both formats as the same secret.

The browser will generate locally with the browser's cryptographic random
number generator and a bundled, pinned wordlist. The page will have no
accounts, analytics, or password history. A standard-library Python CLI will
serve as a reference implementation. The planned web address is
`https://dullroar.com/passphrase/`.

A browser runs the code it receives. If someone replaces the hosted code,
that code can read generated values even over HTTPS. Browser extensions,
clipboard readers, phishing, and device compromise can also expose a secret.
Use a verified offline release or a trusted password-manager generator for
especially sensitive accounts.

The implementation and release are pending. The
[implementation plan](plans/build-passphrase-deck/plan.md) tracks the work and
links to the [Claude launch instructions](plans/build-passphrase-deck/goal.md).

## Repository checks

```sh
python3 scripts/build_indexes.py
python3 scripts/check_context.py
```

## License

See the [proprietary license](LICENSE).
