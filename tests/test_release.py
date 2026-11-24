import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location('package_release', ROOT / 'scripts' / 'package_release.py')
package_release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(package_release)


class SingleFileTest(unittest.TestCase):
    def test_script_opts_out_of_rocket_loader(self):
        html = package_release.build_single().decode('utf-8')
        self.assertEqual(html.count('<script'), 1)
        self.assertIn('<script data-cfasync="false">', html)

    def test_multi_line_import_is_removed(self):
        app = "import {\n  a,\n  b,\n} from './core.js';\nconsole.log(a, b);\n"
        script = package_release.classic_script('export const a = 1;\nexport const b = 2;\n', app)
        self.assertNotIn('import', script)
        self.assertNotIn('export', script)
        self.assertIn('console.log(a, b);', script)


class ProductionNeedsManifestTest(unittest.TestCase):
    def test_production_refuses_to_run_without_manifest(self):
        # The evidence file does not need to exist: the flag check comes first,
        # and the run must make no request.
        result = subprocess.run(
            [sys.executable, str(ROOT / 'scripts' / 'verify_release.py'),
             '--production', 'https://example.invalid/passphrase.html',
             '--evidence', 'no-such-evidence.json'],
            capture_output=True, text=True, timeout=60)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('--manifest', result.stderr)


if __name__ == '__main__':
    unittest.main()
