# Security

Passphrase Deck generates secrets locally. Its strength claims assume a
correct implementation, the verified list, uniform sampling, a working
cryptographic random source, and a private device. A strong generated value
does not protect an account from phishing, reuse, or later disclosure.

A compromised host, injected script, malicious update, or compromised build
dependency can read or replace generated values. Users trust the code they
load on every visit. Review the served code and release checksums. A verified
offline release reduces dependence on the host after verification; it does
not repair an already compromised file or device. Keep dependencies small
and review changes before release.

Browser extensions, clipboard readers, other local software, and device
compromise can expose copied values. Use a trusted device and browser. The
application must not send generated values to a server, store history, or
log them. The operator controls hosting and publication.

Report suspected vulnerabilities privately to the repository owner through
the private channel supplied with the release. Do not include a real
passphrase or other secret in a report. The owner must provide a working
private reporting channel before public distribution.

## Specification review

The specification addresses output collisions, length conditioning, bounded
random sampling, missing randomness, and the deterministic selection of a
scheme. The code must enforce these rules; this document is not an audit of
an implementation. Independent review and real-device checks remain release
gates.
