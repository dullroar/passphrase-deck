#!/usr/bin/env python3
# Run me when: I need to verify the pinned EFF wordlist.
"""Verify the exact upstream file and its structural invariants."""
import hashlib
import itertools
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'data/eff_large_wordlist.txt'
SHA256 = 'addd35536511597a02fa0a9ff1e5284677b8883b83e986e43f15a3db996b903e'


def load_words():
    raw = PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SHA256:
        raise ValueError('wordlist SHA-256 mismatch')
    text = raw.decode('ascii')
    lines = text.splitlines(keepends=True)
    if len(lines) != 7776:
        raise ValueError('wordlist count mismatch')
    words = []
    for line, dice in zip(lines, itertools.product('123456', repeat=5)):
        match = re.fullmatch(r'([1-6]{5})\t([a-z-]+)\n', line)
        if not match or match.group(1) != ''.join(dice):
            raise ValueError('invalid wordlist record or dice order')
        words.append(match.group(2))
    if len(set(words)) != len(words):
        raise ValueError('duplicate word')
    return words


if __name__ == '__main__':
    try:
        words = load_words()
    except (OSError, UnicodeError, ValueError) as exc:
        print(f'wordlist verification failed: {exc}', file=sys.stderr)
        sys.exit(1)
    print(f'wordlist verified: {len(words)} records; SHA-256 {SHA256}')
