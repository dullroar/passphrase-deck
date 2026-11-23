#!/usr/bin/env python3
# Run me when: I need to reproduce the policy entropy and feasibility checks.
"""Count distinct outputs for the schemes in SPEC.md with integer arithmetic."""
from collections import Counter
from itertools import product
from math import log2
from verify_wordlist import load_words

SCHEMES = ((4, 6), (6, 2))


def count_sequences(length_counts, words, digits, minimum, maximum):
    counts = {0: 1}
    for _ in range(words):
        nxt = Counter()
        for total, ways in counts.items():
            for length, size in length_counts.items():
                nxt[total + length] += ways * size
        counts = nxt
    return sum(ways for total, ways in counts.items()
               if minimum <= total + digits + words - 1
               and total + digits + 2 * (words - 1) <= maximum)


def choose(lengths, minimum, maximum, bits):
    for words, digits in SCHEMES:
        count = count_sequences(lengths, words, digits, minimum, maximum)
        outputs = count * 10**digits
        if outputs >= 2**bits:
            return words, digits, count, outputs
    return None


def self_test():
    # Public fixture includes a separator-like hyphen inside a word.
    fixture = ('a', 'a-b', 'ba')
    lengths = Counter(map(len, fixture))
    tuples = [t for t in product(fixture, repeat=2)
              if 3 <= sum(map(len, t)) + 1 and sum(map(len, t)) + 2 <= 7]
    encoded = ['_'.join(t) for t in tuples]
    assert len(encoded) == len(set(encoded))
    assert len(encoded) == count_sequences(lengths, 2, 0, 3, 7)
    # Enumerate every rank through the weighted prefix decoder.
    decoded = []
    for rank in range(len(tuples)):
        for first in fixture:
            suffixes = [t for t in tuples if t[0] == first]
            if rank < len(suffixes):
                decoded.append(suffixes[rank])
                break
            rank -= len(suffixes)
    assert len(decoded) == len(set(decoded)) == len(tuples)
    assert set(decoded) == set(tuples)
    assert choose(lengths, 1, 1, 64) is None


def main():
    self_test()
    lengths = Counter(map(len, load_words()))
    print('length counts:', ', '.join(f'{k}:{v}' for k, v in sorted(lengths.items())))
    for minimum, maximum, bits in ((12, 32, 64), (12, 48, 80), (12, 12, 80)):
        result = choose(lengths, minimum, maximum, bits)
        if result is None:
            print(f'{minimum}-{maximum}, {bits} bits: impossible for supported schemes')
        else:
            words, digits, count, outputs = result
            print(f'{minimum}-{maximum}, {bits} bits: {words} words, {digits} digits; '
                  f'{count} word tuples; {outputs} outputs; {log2(outputs):.6f} bits')
    assert choose(lengths, 12, 32, 64)[:2] == (4, 6)
    assert choose(lengths, 12, 48, 80)[:2] == (6, 2)
    assert choose(lengths, 12, 12, 80) is None
    print('exhaustive fixture and policy checks passed')


if __name__ == '__main__':
    main()
