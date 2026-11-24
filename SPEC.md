# Passphrase specification

## Status

The default keeps the requested 12–32 character range and 64-bit floor.
It uses six independent digits. Review the tradeoffs in
[the feasibility analysis](docs/feasibility.md) before implementation.

## Wordlist

Use the unmodified `data/eff_large_wordlist.txt`. EFF's long list was
retrieved on 2026-11-23 from
<https://www.eff.org/files/2016/07/18/eff_large_wordlist.txt>. Its SHA-256
is `addd35536511597a02fa0a9ff1e5284677b8883b83e986e43f15a3db996b903e`.
An independent published digest appears in
<https://pub.dev/documentation/e2ee_vault/latest/>. The file has 7,776
unique words in ASCII, one dice code and word per line. Words contain
lowercase ASCII letters or hyphens. The original file is unchanged.

Attribute the list to the Electronic Frontier Foundation, link to its source,
and retain the license reference in distributions. EFF's
[copyright policy](https://www.eff.org/copyright) licenses its original site
material under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
unless otherwise noted. The product license does not replace those terms.

## Policy and formats

A policy has integer minimum and maximum lengths and an integer entropy
floor in bits. Accept minimum and maximum from 1 through 128 and entropy floors from
64 through 128. Reject malformed, out-of-range, reversed, or unsupported
values.
Both output lengths must be within the inclusive bounds. Length is the
number of ASCII characters, including spaces and punctuation. Reject a
policy if neither supported scheme meets it. Report `POLICY_UNSUPPORTED`
and suggest a larger maximum or lower target without reducing the configured
floor. Never silently weaken the policy.

The supported schemes, in fixed priority order, are four words with six
digits, then six words with two digits. Preflight counts the valid ordered
word tuples for each scheme, multiplies by 10 to the digit count, multiplies
by the symbol count raised to `count - 1`, and chooses
the first scheme with at least 2 raised to the requested bit floor distinct
outputs. With one symbol the counts are the same as in earlier versions. This choice is deterministic. The default is minimum 12, maximum 32,
and 64 bits. Minimum 12, maximum 48, and 80 bits is also feasible. Do not
claim that all other requests or all higher targets are feasible.

A symbol set is a string of 1 to 32 distinct symbols. The default is
`.,#$_!?` in that order. Each symbol must be a printable ASCII punctuation
character. ASCII has exactly 32 punctuation characters, so the limit of 32
equals the number of allowed characters. A set of all 32 is valid. Reject
letters, digits, space, control characters and non-ASCII characters. Reject a
repeated symbol. The hyphen is allowed (owner decision, 2026-11-24). A word
can contain a hyphen, but this does not make the compact value ambiguous.
The compact value is a concatenation of list words and one-character gap
symbols. Any symbol that is not a letter or a hyphen splits the value
without doubt. A hyphen symbol could be confused with a hyphen inside a word
only if a hyphenated list word were a join of other list words, such as
`a-b` with both `a` and `b` in the list. The four hyphenated list words are
`drop-down`, `felt-tip`, `t-shirt` and `yo-yo`. Their parts `drop`, `felt`,
`tip`, `t` and `yo` are not list words. So no hyphenated word splits. The
Sardinas–Patterson test on the list words and the hyphen proves that the code
is uniquely decodable. A permanent test runs this proof for the real list,
also with capitalization, and checks it by brute force on small lists. The
digits are at the end and have a fixed count, so they never join the parse.
If a future wordlist breaks this proof, the hyphen must be banned again. Reject
the whole set on any bad symbol. Never drop a symbol silently. Report the failed symbol by position and
code point. The symbol set is not a secret.

For each selected tuple, put one symbol and one space after each word except
the last. Each of the `count - 1` gaps has its own independent symbol.
Append the independent decimal digits directly to the last word. The
readable value is this result. The compact value removes only ASCII spaces.
Symbols remain between words; digits remain at the end. Hyphens in the list
remain in the words. Thus both formats are reversibly split into the same
ordered words, gap symbols and digit string. A symbol has one character, so
all lengths and completion counts are the same as with one symbol.

Capitalization is an option. It is off by default. When it is on, change
the first character of each word to upper case and keep all other
characters unchanged. The word length does not change. The option adds no
entropy and does not change the counts, the ranks, or the length checks.
It applies to both formats in the same way. A hyphen in a word stays a
hyphen. The digit count is fixed by the scheme. The symbol set is the only
punctuation option.

Design decision (2026-11-24, owner): the symbol between words is no longer
always an underscore. The user can edit the set of allowed symbols, because
sites have their own odd rules. Symbols add entropy. The restrictive-site
preset keeps its capitalization setting and does not change the set.

Design decision (2026-11-23, owner): many sites require a mix of upper and
lower case letters. A first-letter rule is easy to enter on a phone. A random
case rule is not.

## Uniform selection

For the selected scheme, calculate exact completion counts by remaining
word count and total word length. A tuple is valid only when the compact
length is at least the minimum and the readable length is at most the
maximum. These two checks imply the other two bounds because readable is
always at least as long as compact.

Draw one uniform integer below the total output count. Divide it by
10 raised to the digit count. The remainder is the zero-padded digit string.
Divide the quotient by the symbol count raised to `count - 1`. The remainder
is the symbol rank. Take it by repeated division by the symbol count, which
gives the symbols from the last gap to the first gap. The first gap is the
most significant symbol digit. The final quotient is the zero-based
word-tuple rank. With one symbol the symbol rank is zero. Decode the tuple rank
in list order. At each word position, assign each individual word a weight
equal to the number of valid suffix tuples after that word. Select the word
whose cumulative weight contains the rank and subtract all preceding
weights. Repeat until all positions are filled. Each valid tuple and digit
string has exactly one rank. No random scheme selection or rejected complete
tuple conditions the output. The distinct symbols, distinct words, and
digit alphabet make both format mappings injective. Maximum probability is
exactly one divided by the total output count.

## Secret lifecycle

The page holds a secret only in script memory. The page shows it in the DOM
only while the user reveals it. For each event below, the page drops all
its references to the secret. It also resets the DOM to the hidden state.

| Event | Result |
| --- | --- |
| A change to any generation setting | Clear. |
| An invalid setting | Clear. Do not deal. |
| A new deal | Clear the old secret first. |
| A failed deal | Leave no secret. |
| The tab becomes hidden (`visibilitychange`) | Clear. |
| The page leaves (`pagehide`), or returns from the back/forward cache (`pageshow` with `persisted` true) | Clear. |
| Copy | The page does not clear the clipboard. A copy failure keeps the secret and says so. |
| Logs, errors and telemetry | They never hold a secret. Error text never includes one. |

Dropping references is best-effort disposal. It is not secure memory
erasure. The browser can keep copies in memory that the page cannot reach.

The page has a notice near the result. The entropy bound covers the
generated passphrase only. Choosing a result by its content, or editing it,
lowers the strength. The page adds no storage, no clipboard timer and no
network call for this lifecycle.

Use `secrets.token_bytes()` in Python and `crypto.getRandomValues()` in
the browser. Use unbiased rejection in both runtimes: for a uniformly drawn
unsigned integer in a range of size R, reject values at or above
`R - (R % n)` and reduce accepted values modulo n. For counts above a
single machine word, concatenate enough random bytes, use exact integer
arithmetic, and apply the same rule. Reject invalid n. Bound random rejection
at 128 draws per integer and return `RANDOM_LIMIT` on exhaustion. Do not
return partial output or fall back to a weaker random source. Apply the policy bounds above before allocating memory. Use exact integers
and reject any calculation the runtime cannot represent.

Production interfaces never accept an injected random source. Tests may
exercise internal functions with public controlled streams. The build, tests,
and formatting rules are deterministic. Every production deal uses fresh
cryptographic randomness. Never record generated passphrases in logs or
telemetry.
