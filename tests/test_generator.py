import contextlib
import hashlib
import importlib.util
import io
import itertools
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('passphrase_reference', ROOT / 'python/passphrase.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


class GeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.words = generator.load_words()
        cls.fixture = json.loads((ROOT / 'tests/fixtures/parity.json').read_text())

    def test_wordlist_validation(self):
        self.assertEqual(len(self.words), 7776)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'list'
            path.write_bytes(b'public corrupt fixture\n')
            with self.assertRaisesRegex(ValueError, 'wordlist verification failed'):
                generator.load_words(path)
            raw = generator.WORDLIST.read_bytes()
            records = raw.splitlines(keepends=True)
            mutations = [
                b''.join(records[:-1]),
                raw.replace(b'11111\t', b'11112\t', 1),
                raw.replace(records[1], records[1].split(b'\t')[0] + b'\t' + records[0].split(b'\t')[1], 1),
                raw.replace(b'abacus', b'aba cus', 1),
                raw.replace(b'abacus', b'\xff', 1),
            ]
            for contents in mutations:
                path.write_bytes(contents)
                with mock.patch.object(generator, 'DIGEST', hashlib.sha256(contents).hexdigest()):
                    with self.assertRaises((ValueError, UnicodeError)):
                        generator.load_words(path)

    def test_policy_and_bounds(self):
        count, digits, outputs, _ = generator.select_policy(self.words, 12, 32, 64, '_')
        self.assertEqual((count, digits, outputs), (4, 6, 36742626714313000000))
        self.assertEqual(generator.select_policy(self.words, 12, 48, 80, '_')[:3],
                         (6, 2, 1767490168328080038268500))
        # The default set has 7 symbols. Each of the count - 1 gaps adds a factor of 7.
        self.assertEqual(generator.select_policy(self.words, 12, 32, 64)[:3],
                         (4, 6, 36742626714313000000 * 7 ** 3))
        for args in ((0, 32, 64), (33, 32, 64), (12, 129, 64),
                     (12, 32, 63), (12, 12, 80), (True, 32, 64)):
            with self.subTest(policy=args), self.assertRaises(generator.PolicyError):
                generator.select_policy(self.words, *args)

    def test_vectors_and_exhaustive_rank_mapping(self):
        f = self.fixture
        words = f['words']
        count, digits = f['word_count'], f['digits']
        suffix = generator._completions(words, count, digits, f['minimum'], f['maximum'])
        for vector in f['vectors']:
            self.assertEqual(generator._unrank(words, count, digits, vector['rank'], suffix),
                             (vector['readable'], vector['compact']))
        expected = set()
        for parts in itertools.product(words, repeat=count):
            for digit in range(10 ** digits):
                readable = '_ '.join(parts) + str(digit).zfill(digits)
                compact = readable.replace(' ', '')
                if f['minimum'] <= len(compact) and len(readable) <= f['maximum']:
                    expected.add((readable, compact))
        total = suffix(count, 0) * 10 ** digits
        actual = [generator._unrank(words, count, digits, rank, suffix)
                  for rank in range(total)]
        self.assertEqual(len(actual), len(set(actual)))
        self.assertEqual(set(actual), expected)

    def test_symbol_set_vectors_and_exhaustive_rank_mapping(self):
        f = self.fixture['symbol_set']
        words, symbols = f['words'], f['symbols']
        count, digits = f['word_count'], f['digits']
        suffix = generator._completions(words, count, digits, f['minimum'], f['maximum'])
        for vector in f['vectors']:
            self.assertEqual(
                generator._unrank(words, count, digits, vector['rank'], suffix, False, symbols),
                (vector['readable'], vector['compact']))
        expected = set()
        for parts in itertools.product(words, repeat=count):
            for gaps in itertools.product(symbols, repeat=count - 1):
                for digit in range(10 ** digits):
                    readable = ''.join(w + g + ' ' for w, g in zip(parts, gaps))
                    readable += parts[-1] + str(digit).zfill(digits)
                    compact = readable.replace(' ', '')
                    if f['minimum'] <= len(compact) and len(readable) <= f['maximum']:
                        expected.add((readable, compact))
        total = suffix(count, 0) * 10 ** digits * len(symbols) ** (count - 1)
        actual = [generator._unrank(words, count, digits, rank, suffix, False, symbols)
                  for rank in range(total)]
        self.assertEqual(len(actual), len(set(actual)))
        self.assertEqual(set(actual), expected)

    def test_symbol_validation(self):
        good = ['_', '.,#$_!?', '<&">\'', generator.DEFAULT_SYMBOLS,
                ''.join(sorted(generator.ALLOWED_SYMBOLS))[:32]]
        for symbols in good:
            self.assertEqual(len(generator.validate_symbols(symbols)), len(symbols))
        bad = ['', 'a', 'A', '1', ' ', '-', 'a.', '..', '.,.', '\t', '\x00', 'é', '.é',
               'x' * 33, '%' * 33, None, 5, ['.']]
        for symbols in bad:
            with self.subTest(symbols=symbols), self.assertRaises(generator.PolicyError):
                generator.validate_symbols(symbols)
        with self.assertRaisesRegex(generator.PolicyError, r'symbol 2 \(U\+0061\)'):
            generator.validate_symbols('.a')

    def test_symbol_count_sets_entropy_and_one_symbol_matches_old_counts(self):
        one = generator.select_policy(self.words, 12, 32, 64, '.')
        self.assertEqual(one[:3], (4, 6, 36742626714313000000))
        # Three words need no symbol factor beyond the gaps; more symbols give more outputs.
        self.assertGreater(generator.select_policy(self.words, 12, 32, 64, '.,')[2], one[2])

    def test_symbols_in_real_output(self):
        count, digits, total, suffix = generator.select_policy(self.words, 12, 32, 64)
        for rank in (0, total // 3, total - 1):
            readable, compact = generator._unrank(
                self.words, count, digits, rank, suffix, True, generator.DEFAULT_SYMBOLS)
            self.assertEqual(compact, readable.replace(' ', ''))
            self.assertTrue(12 <= len(compact) and len(readable) <= 32)
            self.assertEqual(len(readable.split(' ')), count)
            for part in readable.split(' ')[:-1]:
                self.assertIn(part[-1], generator.DEFAULT_SYMBOLS)
        with self.assertRaises(generator.PolicyError):
            generator.select_policy(self.words, 12, 32, 64, '.a')

    def test_cli_symbols(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(generator.secrets, 'token_bytes', side_effect=lambda n: bytes(n)):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = generator.main(['--symbols', '%'])
        self.assertEqual(result, 0)
        self.assertRegex(stdout.getvalue().splitlines()[0], r'^[a-z-]+(% [a-z-]+)+\d+$')
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = generator.main(['--symbols', '-'])
        self.assertEqual(result, 1)
        self.assertEqual(stdout.getvalue(), '')
        self.assertIn('SYMBOLS_INVALID', stderr.getvalue())

    def test_real_list_rank_boundaries(self):
        for minimum, maximum, entropy in ((12, 32, 64), (12, 48, 80)):
            count, digits, total, suffix = generator.select_policy(
                self.words, minimum, maximum, entropy, '_')
            for rank in (0, total // 2, total - 1):
                readable, compact = generator._unrank(self.words, count, digits, rank, suffix)
                self.assertEqual(compact, readable.replace(' ', ''))
                self.assertTrue(minimum <= len(readable) <= maximum)
                self.assertTrue(minimum <= len(compact) <= maximum)

    def test_capitalize_option(self):
        f = self.fixture
        words = f['words']
        count, digits = f['word_count'], f['digits']
        suffix = generator._completions(words, count, digits, f['minimum'], f['maximum'])
        for vector in f['vectors']:
            plain = generator._unrank(words, count, digits, vector['rank'], suffix)
            caps = generator._unrank(words, count, digits, vector['rank'], suffix, True)
            self.assertEqual(len(caps[0]), len(plain[0]))
            self.assertEqual(caps[1], caps[0].replace(' ', ''))
            self.assertEqual(caps[0].lower(), plain[0].lower())
            for word in caps[0].split('_ ')[:count]:
                self.assertTrue(word[0].isupper())

    def test_unbiased_rejection_and_limit(self):
        # One-byte values 250–255 are rejected for n=10.
        values = iter((b'\xff', b'\x14'))
        self.assertEqual(generator._randbelow(10, lambda _: next(values)), 0)
        values = [generator._randbelow(10, lambda _, i=i: bytes([i]))
                  for i in range(250)]
        self.assertEqual([values.count(i) for i in range(10)], [25] * 10)
        draw = mock.Mock(return_value=b'\xff')
        with self.assertRaises(generator.RandomLimitError):
            generator._randbelow(10, draw)
        self.assertEqual(draw.call_count, 128)
        with self.assertRaises(ValueError):
            generator._randbelow(0, lambda _: b'')
        with self.assertRaises(ValueError):
            generator._randbelow(10, lambda _: b'')

    def test_production_source_and_lengths(self):
        source = mock.Mock(side_effect=lambda n: bytes(n))
        with mock.patch.object(generator.secrets, 'token_bytes', source):
            for _ in range(2):
                readable, compact = generator.generate(self.words)
                self.assertEqual(readable.replace(' ', ''), compact)
                self.assertTrue(12 <= len(readable) <= 32)
                self.assertTrue(12 <= len(compact) <= 32)
                self.assertRegex(readable, r'^[a-z.,#$_!?0-9 -]+$')
        self.assertEqual(source.call_count, 2)

    def test_cli_controlled_and_errors(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(generator.secrets, 'token_bytes', side_effect=lambda n: bytes(n)):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = generator.main(['--count', '2'])
        self.assertEqual(result, 0)
        self.assertEqual(len(stdout.getvalue().splitlines()), 4)
        self.assertEqual(stderr.getvalue(), '')
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = generator.main(['--max', '12', '--entropy', '80'])
        self.assertEqual(result, 1)
        self.assertEqual(stdout.getvalue(), '')
        self.assertIn('POLICY_UNSUPPORTED', stderr.getvalue())


if __name__ == '__main__':
    unittest.main()
