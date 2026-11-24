#!/usr/bin/env python3
"""Generate a passphrase pair using the policy in SPEC.md."""
import argparse
from collections import Counter
from functools import lru_cache
import hashlib
import itertools
from pathlib import Path
import re
import secrets
import string
import sys

WORDLIST = Path(__file__).resolve().parent.parent / 'data' / 'eff_large_wordlist.txt'
DIGEST = 'addd35536511597a02fa0a9ff1e5284677b8883b83e986e43f15a3db996b903e'
SCHEMES = ((4, 6), (6, 2))
DEFAULT_SYMBOLS = '.,#$_!?'
ALLOWED_SYMBOLS = frozenset(string.punctuation)
MAX_SYMBOLS = 32


class PolicyError(ValueError):
    pass


class RandomLimitError(RuntimeError):
    pass


def validate_symbols(symbols):
    """Return the symbols as a tuple. Reject the whole set on any bad symbol."""
    if not isinstance(symbols, str) or not 1 <= len(symbols) <= MAX_SYMBOLS:
        raise PolicyError(f'SYMBOLS_INVALID: use 1 to {MAX_SYMBOLS} symbols')
    seen = set()
    for position, char in enumerate(symbols, 1):
        if char not in ALLOWED_SYMBOLS:
            raise PolicyError(f'SYMBOLS_INVALID: symbol {position} (U+{ord(char):04X}) '
                              'is not an allowed punctuation character')
        if char in seen:
            raise PolicyError(f'SYMBOLS_INVALID: symbol {position} (U+{ord(char):04X}) '
                              'is repeated')
        seen.add(char)
    return tuple(symbols)


def load_words(path=WORDLIST):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != DIGEST:
        raise ValueError('wordlist verification failed')
    lines = raw.decode('ascii').splitlines(keepends=True)
    if len(lines) != 7776:
        raise ValueError('wordlist verification failed')
    words = []
    for line, code in zip(lines, itertools.product('123456', repeat=5)):
        match = re.fullmatch(r'([1-6]{5})\t([a-z-]+)\n', line)
        if not match or match.group(1) != ''.join(code):
            raise ValueError('wordlist verification failed')
        words.append(match.group(2))
    if len(set(words)) != 7776:
        raise ValueError('wordlist verification failed')
    return tuple(words)


def _completions(words, count, digits, minimum, maximum):
    lengths = Counter(map(len, words))

    @lru_cache(maxsize=None)
    def suffix(remaining, length):
        if not remaining:
            return int(minimum <= length + digits + count - 1 and
                       length + digits + 2 * (count - 1) <= maximum)
        return sum(quantity * suffix(remaining - 1, length + size)
                   for size, quantity in lengths.items())

    return suffix


def select_policy(words, minimum, maximum, entropy, symbols=DEFAULT_SYMBOLS):
    if (any(type(value) is not int for value in (minimum, maximum, entropy)) or
            not 1 <= minimum <= maximum <= 128 or not 64 <= entropy <= 128):
        raise PolicyError('invalid policy bounds')
    symbol_count = len(validate_symbols(symbols))
    for count, digits in SCHEMES:
        suffix = _completions(words, count, digits, minimum, maximum)
        tuples = suffix(count, 0)
        outputs = tuples * 10 ** digits * symbol_count ** (count - 1)
        if outputs >= 1 << entropy:
            return count, digits, outputs, suffix
    raise PolicyError('POLICY_UNSUPPORTED: increase maximum or lower entropy target')


def _unrank(words, count, digits, rank, suffix, capitalize=False, symbols='_'):
    symbols = validate_symbols(symbols)
    quotient, digit_rank = divmod(rank, 10 ** digits)
    tuple_rank, symbol_rank = divmod(quotient, len(symbols) ** (count - 1))
    gaps = []
    for _ in range(count - 1):
        symbol_rank, index = divmod(symbol_rank, len(symbols))
        gaps.append(symbols[index])
    gaps.reverse()
    selected = []
    length = 0
    for remaining in range(count - 1, -1, -1):
        for word in words:
            weight = suffix(remaining, length + len(word))
            if tuple_rank < weight:
                selected.append(word)
                length += len(word)
                break
            tuple_rank -= weight
        else:
            raise ValueError('rank outside valid range')
    if tuple_rank:
        raise ValueError('rank outside valid range')
    if capitalize:
        selected = [word[0].upper() + word[1:] for word in selected]
    readable = ''.join(word + gap + ' ' for word, gap in zip(selected, gaps))
    readable += selected[-1] + str(digit_rank).zfill(digits)
    return readable, readable.replace(' ', '')


def _randbelow(n, draw):
    if type(n) is not int or n <= 0:
        raise ValueError('invalid random bound')
    size = max(1, (n.bit_length() + 7) // 8)
    source_range = 1 << (8 * size)
    limit = source_range - source_range % n
    for _ in range(128):
        raw = draw(size)
        if not isinstance(raw, bytes) or len(raw) != size:
            raise ValueError('random source failure')
        value = int.from_bytes(raw, 'big')
        if value < limit:
            return value % n
    raise RandomLimitError('RANDOM_LIMIT')


def generate(words, minimum=12, maximum=32, entropy=64, capitalize=False,
             symbols=DEFAULT_SYMBOLS):
    count, digits, outputs, suffix = select_policy(words, minimum, maximum, entropy, symbols)
    rank = _randbelow(outputs, secrets.token_bytes)
    return _unrank(words, count, digits, rank, suffix, capitalize, symbols)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Generate a local passphrase in two formats.')
    parser.add_argument('--min', dest='minimum', type=int, default=12)
    parser.add_argument('--max', dest='maximum', type=int, default=32)
    parser.add_argument('--entropy', type=int, default=64)
    parser.add_argument('--capitalize', action='store_true',
                        help='capitalize the first letter of each word')
    parser.add_argument('--symbols', default=DEFAULT_SYMBOLS,
                        help='separator symbols, 1 to 32 distinct punctuation characters')
    parser.add_argument('--count', type=int, default=1, help='number of pairs (1–1000)')
    args = parser.parse_args(argv)
    if not 1 <= args.count <= 1000:
        parser.error('--count must be between 1 and 1000')
    try:
        words = load_words()
        select_policy(words, args.minimum, args.maximum, args.entropy, args.symbols)
        for _ in range(args.count):
            readable, compact = generate(words, args.minimum, args.maximum, args.entropy,
                                           args.capitalize, args.symbols)
            print(readable)
            print(compact)
    except (OSError, UnicodeError, ValueError, RandomLimitError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
