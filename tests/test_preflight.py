"""Test the policy preflight. It is pure: no random source, no secret.

The table in tests/fixtures/preflight.json is shared with the browser tests.
Both implementations must give the same state, code, scheme and bit count.
"""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('passphrase', ROOT / 'python' / 'passphrase.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)

CASES = json.loads((ROOT / 'tests' / 'fixtures' / 'preflight.json').read_text())


class PreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.words = generator.load_words()

    def run_case(self, settings):
        return generator.preflight(self.words, settings['minimum'], settings['maximum'],
                                   settings['entropy'], settings['symbols'])

    def test_table_has_all_three_states(self):
        states = {case['expect']['state'] for case in CASES}
        self.assertEqual(states, {'malformed', 'unsupported', 'valid'})

    def test_table_results(self):
        for case in CASES:
            result = self.run_case(case['settings'])
            message = result.pop('message', None)
            self.assertEqual(result, case['expect'], case['settings'])
            if result['state'] != 'valid':
                self.assertTrue(message)

    def test_valid_bits_meet_the_floor(self):
        for case in CASES:
            if case['expect']['state'] == 'valid':
                self.assertGreaterEqual(case['expect']['bits'], case['settings']['entropy'])

    def test_preflight_matches_select_policy(self):
        for case in CASES:
            s = case['settings']
            result = self.run_case(s)
            try:
                count, digits, outputs, _ = generator.select_policy(
                    self.words, s['minimum'], s['maximum'], s['entropy'], s['symbols'])
            except generator.PolicyError as exc:
                self.assertEqual(result['code'], exc.code)
            else:
                self.assertEqual((result['count'], result['digits'], result['bits']),
                                 (count, digits, outputs.bit_length() - 1))

    def test_preflight_does_not_call_the_random_source(self):
        with mock.patch.object(generator.secrets, 'token_bytes',
                               side_effect=AssertionError('random source called')) as draw, \
                mock.patch.object(generator, '_randbelow',
                                  side_effect=AssertionError('random source called')) as below:
            for case in CASES:
                self.run_case(case['settings'])
        draw.assert_not_called()
        below.assert_not_called()


if __name__ == '__main__':
    unittest.main()
