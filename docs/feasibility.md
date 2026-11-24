# Policy feasibility

Run `python3 scripts/check_feasibility.py` after wordlist verification. It
counts ordered tuples with integer dynamic programming. Length includes the
four hyphenated list entries as recorded, not as separate words.

| Word length | Count |
| --- | ---: |
| 3 | 82 |
| 4 | 467 |
| 5 | 928 |
| 6 | 1,372 |
| 7 | 1,591 |
| 8 | 1,779 |
| 9 | 1,557 |

The readable separator is one symbol and one space. It has two ASCII
characters. The compact separator is the symbol. It has one. A symbol is one
character, so the symbol choice does not change any length. The exhaustive
fixture measures formatted strings directly and checks the length
calculation.

With the format and sampling in [SPEC.md](../SPEC.md), 12–32 characters
and 64 bits selects four words and six digits. There are 36,742,626,714,313
valid word tuples. With a set of one symbol there are
36,742,626,714,313,000,000 distinct outputs. The
min-entropy is approximately 64.994089 bits in each copyable format.
Each gap between words adds a factor equal to the symbol count. The default
set has seven symbols and four words have three gaps. This multiplies the
count by 343 and adds approximately 8.42 bits.

For 12–48 characters and 80 bits, six words and two digits give, with one
symbol, 1,767,490,168,328,080,038,268,500 outputs and approximately
80.547976 bits.
The 12–12 and 80-bit policy is impossible for the supported schemes. This
is not a proof that every conceivable scheme is impossible.

The count gives a min-entropy bound only with the uniform rank selection
and exact formatting in the specification. Each valid tuple has equal
probability. Every digit string has equal probability and is independent.
The compact mapping keeps the symbols. A symbol can be a hyphen. Distinct
tuples still do not collide, even when a word contains a hyphen. No list word
that has a hyphen splits into two list words. The words and the hyphen form a
uniquely decodable code. [SPEC.md](../SPEC.md) and the tests state the proof.
A fixed scheme selection has probability
one. An exhausted random draw returns an error, so conditional on success
the one accepted rank is uniform even with a fixed rejection bound.
The script uses a small exhaustive public word fixture to check tuple counts
and collision handling. Production must test rank decoding separately.

The six digits in the proposed default affect memorability. A longer maximum
allows a six-word, two-digit policy with an 80-bit floor. An independently
audited short-word list could improve length and memorability but adds a
provenance and review task. More independent symbols or digits can add
entropy but make typing harder. The selected default keeps the requested length range and wordlist.
