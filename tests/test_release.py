import importlib.util
from pathlib import Path
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


if __name__ == '__main__':
    unittest.main()
