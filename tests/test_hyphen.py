"""Prove that a hyphen symbol keeps the compact format uniquely decodable.

The compact value is a concatenation of list words and one-character gap
symbols, then the digits. A symbol that is not a letter or a hyphen cannot
occur in a word, so it always splits the value. Only a hyphen symbol can be
confused with a hyphen inside a word. The Sardinas-Patterson test decides
exactly whether the code (the words and the hyphen) is uniquely decodable.
"""
import importlib.util
import itertools
from pathlib import Path
import string
import unittest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('passphrase', ROOT / 'python' / 'passphrase.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


def uniquely_decodable(code):
    """Sardinas-Patterson test. Return True if every concatenation decodes one way."""
    code = set(code)
    if '' in code:
        return False

    def dangling(left, right):
        return {b[len(a):] for a in left for b in right if a != b and b.startswith(a)}

    current = dangling(code, code)
    seen = set()
    while current:
        if current & code:
            return False
        key = frozenset(current)
        if key in seen:
            return True
        seen.add(key)
        current = dangling(code, current) | dangling(current, code)
    return True


def brute_force_unique(words, symbols, count):
    """Return True if no two (words, gap symbols) choices give the same compact value."""
    seen = set()
    for tuple_ in itertools.product(words, repeat=count):
        for gaps in itertools.product(symbols, repeat=count - 1):
            text = tuple_[0] + ''.join(g + w for g, w in zip(gaps, tuple_[1:]))
            if text in seen:
                return False
            seen.add(text)
    return True


class HyphenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.words = generator.load_words()

    def test_hyphen_is_an_allowed_symbol(self):
        self.assertIn('-', generator.ALLOWED_SYMBOLS)
        self.assertEqual(generator.validate_symbols('-'), ('-',))
        self.assertEqual(generator.validate_symbols('.-,'), ('.', '-', ','))

    def test_limit_equals_allowed_characters(self):
        self.assertEqual(len(generator.ALLOWED_SYMBOLS), 32)
        self.assertEqual(generator.MAX_SYMBOLS, 32)
        full = ''.join(sorted(generator.ALLOWED_SYMBOLS))
        self.assertEqual(len(generator.validate_symbols(full)), 32)
        self.assertEqual(generator.select_policy(self.words, 12, 32, 64, full)[0], 4)
        with self.assertRaises(generator.PolicyError):
            generator.validate_symbols(full + '.')

    def test_real_list_with_hyphen_is_uniquely_decodable(self):
        hyphenated = [w for w in self.words if '-' in w]
        self.assertEqual(sorted(hyphenated), ['drop-down', 'felt-tip', 't-shirt', 'yo-yo'])
        word_set = set(self.words)
        for word in hyphenated:
            parts = word.split('-')
            self.assertFalse(all(part in word_set for part in parts), word)
        self.assertTrue(uniquely_decodable(set(self.words) | {'-'}))
        capitalized = {w[0].upper() + w[1:] for w in self.words}
        self.assertTrue(uniquely_decodable(capitalized | {'-'}))

    def test_digits_and_other_symbols_cannot_join_the_parse(self):
        alphabet = set(string.ascii_lowercase + '-')
        self.assertTrue(all(set(w) <= alphabet for w in self.words))
        others = set(generator.ALLOWED_SYMBOLS) - {'-'}
        self.assertFalse(others & alphabet)
        self.assertFalse(set(string.digits) & (alphabet | set(string.punctuation)))

    def test_detector_agrees_with_brute_force_on_small_lists(self):
        # A list where hyphenated words are joins of list words must collide.
        bad = ('drop', 'down', 'drop-down', 'felt', 'tip', 'felt-tip')
        self.assertFalse(uniquely_decodable(set(bad) | {'-'}))
        self.assertFalse(brute_force_unique(bad, '-', 3))
        # The colliding example: two parses of one compact value.
        self.assertEqual('drop-down' + '-' + 'felt' + '-' + 'tip',
                         'drop' + '-' + 'down' + '-' + 'felt-tip')
        # A list with hyphenated words that do not split is safe.
        good = ('a', 'ba', 'ca-b', 'c-ba')
        self.assertTrue(uniquely_decodable(set(good) | {'-'}))
        for count in (2, 3):
            self.assertTrue(brute_force_unique(good, '-', count))
            self.assertTrue(brute_force_unique(good, '.-', count))

    def test_brute_force_on_real_hyphenated_words_and_their_parts(self):
        word_set = set(self.words)
        hyphenated = [w for w in self.words if '-' in w]
        parts = {p for w in hyphenated for p in w.split('-')} & word_set
        subset = hyphenated + sorted(parts)
        self.assertTrue(brute_force_unique(subset, '-', 3))
        self.assertTrue(brute_force_unique(subset, '.-', 3))


if __name__ == '__main__':
    unittest.main()
