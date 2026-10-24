"""Site branding cannot admit unapproved scientific media or changed bytes."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from public_gallery_media import validate_media


class SiteBrandingTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / 'data').mkdir()
        self.source = self.root / 'static/site-branding/site-logo.png'
        self.source.parent.mkdir(parents=True)
        self.source.write_bytes(b'synthetic owner branding')
        self.entry = dict(path='static/site-branding/site-logo.png',
                          sha256=hashlib.sha256(self.source.read_bytes()).hexdigest())
        self.save()

    def save(self):
        (self.root / 'data/site-branding.json').write_text(json.dumps(
            dict(schema_version=1, files=[self.entry])), encoding='utf-8')

    def validate(self, output=None):
        return validate_media(self.root, dict(records=[]), dict(approved_records=[]), output)

    def test_exact_branding_source_and_output(self):
        self.assertEqual(self.validate(), {self.entry['path']})
        output = self.root / 'output'
        target = output / 'site-branding/site-logo.png'
        target.parent.mkdir(parents=True)
        target.write_bytes(self.source.read_bytes())
        self.validate(output)
        target.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'Published site branding'):
            self.validate(output)

    def test_source_change_rejected(self):
        self.source.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'branding bytes changed'):
            self.validate()

    def test_scientific_images_cannot_be_branding(self):
        for name in ('static/figures/approved/figure.png', 'static/site-branding/paper.png',
                     'static/site-branding/../../private.png'):
            with self.subTest(name=name):
                self.entry['path'] = name
                self.save()
                with self.assertRaisesRegex(ValueError, 'branding path'):
                    self.validate()

    def test_branding_does_not_exempt_extra_rasters_or_icons(self):
        for name in ('unreviewed.png', 'unreviewed.ico'):
            path = self.source.with_name(name)
            path.write_bytes(b'not approved')
            with self.assertRaisesRegex(ValueError, 'Unapproved raster'):
                self.validate()
            path.unlink()

    def test_duplicate_entries_rejected(self):
        (self.root / 'data/site-branding.json').write_text(json.dumps(
            dict(schema_version=1, files=[self.entry, self.entry])), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.validate()


if __name__ == '__main__':
    unittest.main()
