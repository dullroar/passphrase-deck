"""Exhaustive rank tests on tiny synthetic dictionaries.

The brute-force reference below builds every output from scratch. It shares no
code with the counting code in python/passphrase.py. The fixture
tests/fixtures/exhaustive.json holds the public result for the browser tests.
To rewrite the fixture after a deliberate change, set UPDATE_EXHAUSTIVE=1.
"""
import importlib.util
import itertools
import json
import os
from pathlib import Path
import random
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/fixtures/exhaustive.json'
spec = importlib.util.spec_from_file_location('passphrase_reference', ROOT / 'python/passphrase.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)

MAX_TOTAL = 700
SEED = 20260101


def brute_force(words, count, digits, minimum, maximum, symbols, capitalize=False):
    """Return the set of (readable, compact) pairs that meet the length rules."""
    found = []
    for chosen in itertools.product(words, repeat=count):
        shown = [w.capitalize() if capitalize else w for w in chosen]
        for gaps in itertools.product(symbols, repeat=count - 1):
            for number in range(10 ** digits):
                readable = ''.join(w + g + ' ' for w, g in zip(shown, gaps))
                readable += shown[-1] + str(number).zfill(digits)
                compact = readable.replace(' ', '')
                if minimum <= len(compact) and len(readable) <= maximum:
                    found.append((readable, compact))
    return found


def make_cases():
    """Build tiny dictionaries and policies from a fixed seed."""
    rng = random.Random(SEED)
    cases = []
    while len(cases) < 6:
        size = rng.randint(3, 5)
        words = set()
        while len(words) < size:
            words.add(''.join(rng.choice('abcdefgh') for _ in range(rng.randint(1, 4))))
        words = sorted(words)
        count = rng.randint(2, 3)
        digits = rng.randint(1, 2)
        symbols = ''.join(rng.sample('.,#_!', rng.randint(1, 3)))
        minimum = rng.randint(3, 10)
        maximum = rng.randint(minimum, minimum + 8)
        everything = len(words) ** count * len(symbols) ** (count - 1) * 10 ** digits
        total = len(brute_force(words, count, digits, minimum, maximum, symbols))
        if everything > 4 * MAX_TOTAL or not 0 < total <= MAX_TOTAL or total == everything:
            continue
        cases.append({'words': words, 'word_count': count, 'digits': digits,
                      'minimum': minimum, 'maximum': maximum, 'symbols': symbols})
    return cases


def unrank_all(case, capitalize=False):
    suffix = generator._completions(case['words'], case['word_count'], case['digits'],
                                    case['minimum'], case['maximum'])
    total = (suffix(case['word_count'], 0) * 10 ** case['digits'] *
             len(case['symbols']) ** (case['word_count'] - 1))
    outputs = [list(generator._unrank(case['words'], case['word_count'], case['digits'], rank,
                                      suffix, capitalize, case['symbols']))
               for rank in range(total)]
    return total, outputs, suffix


class ExhaustiveRankTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = make_cases()

    def test_cases_are_nontrivial(self):
        self.assertEqual(len(self.cases), 6)
        for case in self.cases:
            self.assertEqual(len(set(case['words'])), len(case['words']))

    def test_every_rank_matches_brute_force(self):
        for case in self.cases:
            args = (case['words'], case['word_count'], case['digits'], case['minimum'],
                    case['maximum'], case['symbols'])
            expected = brute_force(*args)
            total, outputs, _ = unrank_all(case)
            self.assertEqual(total, len(expected))
            self.assertEqual(len(outputs), total)
            readable = [pair[0] for pair in outputs]
            compact = [pair[1] for pair in outputs]
            self.assertEqual(len(set(readable)), total)
            self.assertEqual(len(set(compact)), total)
            self.assertEqual({tuple(pair) for pair in outputs}, set(expected))
            for text, short in outputs:
                self.assertGreaterEqual(len(short), case['minimum'])
                self.assertLessEqual(len(text), case['maximum'])

    def test_outputs_split_back(self):
        for case in self.cases:
            word = '|'.join(map(re.escape, case['words']))
            symbol = '[' + re.escape(case['symbols']) + ']'
            count, digits = case['word_count'], case['digits']
            readable_re = re.compile(rf'(?:({word})({symbol}) ){{{count - 1}}}({word})(\d{{{digits}}})')
            compact_re = re.compile(rf'(?:({word})({symbol})){{{count - 1}}}({word})(\d{{{digits}}})')
            _, outputs, _ = unrank_all(case)
            for text, short in outputs:
                self.assertIsNotNone(readable_re.fullmatch(text))
                self.assertIsNotNone(compact_re.fullmatch(short))
                self.assertEqual(text.replace(' ', ''), short)

    def test_length_limits_remove_exactly_the_expected_outputs(self):
        removed_any = False
        for case in self.cases:
            base = (case['words'], case['word_count'], case['digits'])
            wide = set(brute_force(*base, 1, 128, case['symbols']))
            _, outputs, _ = unrank_all(case)
            kept = {tuple(pair) for pair in outputs}
            self.assertLessEqual(kept, wide)
            for text, short in wide - kept:
                self.assertTrue(len(short) < case['minimum'] or len(text) > case['maximum'])
            for text, short in kept:
                self.assertTrue(case['minimum'] <= len(short) and len(text) <= case['maximum'])
            removed_any = removed_any or len(kept) < len(wide)
        self.assertTrue(removed_any)

    def test_capitalization_keeps_count_and_distinctness(self):
        for case in self.cases:
            total, plain, _ = unrank_all(case)
            _, capital, _ = unrank_all(case, capitalize=True)
            self.assertEqual(len(capital), total)
            self.assertEqual(len({p[0] for p in capital}), total)
            self.assertEqual(len({p[1] for p in capital}), total)
            expected = brute_force(case['words'], case['word_count'], case['digits'],
                                   case['minimum'], case['maximum'], case['symbols'], True)
            self.assertEqual({tuple(p) for p in capital}, set(expected))
            for (a, _), (b, _) in zip(plain, capital):
                self.assertEqual(a.lower(), b.lower())

    def test_rank_outside_the_range_fails(self):
        case = self.cases[0]
        total, _, suffix = unrank_all(case)
        with self.assertRaises(ValueError):
            generator._unrank(case['words'], case['word_count'], case['digits'],
                              total * 1000, suffix, False, case['symbols'])

    def test_fixture_matches_python(self):
        data = {'cases': []}
        for case in self.cases:
            total, outputs, _ = unrank_all(case)
            data['cases'].append(dict(case, total=total, outputs=outputs))
        if os.environ.get('UPDATE_EXHAUSTIVE') == '1':
            FIXTURE.write_text(json.dumps(data, separators=(',', ':')) + '\n')
        self.assertEqual(json.loads(FIXTURE.read_text()), data)


class RandomBoundaryTests(unittest.TestCase):
    @staticmethod
    def source(values, size):
        queue = iter(values)

        def draw(wanted):
            assert wanted == size
            return next(queue).to_bytes(size, 'big')
        return draw

    def test_largest_accepted_and_first_rejected_value(self):
        # n = 1000 needs 2 bytes. The limit is 65536 - 536 = 65000.
        self.assertEqual(generator._randbelow(1000, self.source([64999], 2)), 999)
        self.assertEqual(generator._randbelow(1000, self.source([65000, 7], 2)), 7)
        self.assertEqual(generator._randbelow(1000, self.source([65535, 1234], 2)), 234)
        self.assertEqual(generator._randbelow(1000, self.source([0], 2)), 0)

    def test_draw_limit(self):
        self.assertEqual(generator._randbelow(1000, self.source([65000] * 127 + [5], 2)), 5)
        calls = []

        def draw(size):
            calls.append(size)
            return (65000).to_bytes(size, 'big')
        with self.assertRaises(generator.RandomLimitError) as caught:
            generator._randbelow(1000, draw)
        self.assertEqual(len(calls), 128)
        self.assertEqual(str(caught.exception), 'RANDOM_LIMIT')

    def test_bad_source_and_bound(self):
        with self.assertRaises(ValueError):
            generator._randbelow(0, lambda size: b'\0' * size)
        with self.assertRaises(ValueError):
            generator._randbelow(1000, lambda size: b'\0')


if __name__ == '__main__':
    unittest.main()
