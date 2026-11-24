# Python reference

Run `python3 python/passphrase.py` to print one pair. Use `--min`, `--max`,
`--entropy`, and `--count` to set the policy and request a batch. Use
`--symbols` to set the separator symbols. The default is `.,#$_!?`. Run with
`--help` for the options. The default prints two lines: readable, then
compact. Batch mode repeats this pair of lines.

The program writes passphrases to stdout. Terminal scrollback, shell capture,
redirected output, and clipboard readers can expose them. Use a trusted device
and handle stdout and the clipboard as secrets. The program does not write
files or keep a history. A failure in batch mode can occur after earlier pairs
have been printed.
