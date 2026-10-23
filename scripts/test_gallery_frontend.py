"""Run the dependency-free browser-helper tests when Node is available locally."""
from pathlib import Path
import shutil
import subprocess
import unittest


class GalleryFrontendTest(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node is needed for Gallery helper tests')
    def test_search_and_palette_helpers(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(['node', '--test', 'scripts/test_gallery_frontend.cjs'],
                                cwd=root, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
