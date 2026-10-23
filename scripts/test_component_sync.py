"""Isolated Git fixtures: no network, original FIG access, or real repo mutation."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest
import uuid

from check_gallery_component import content_hash, validate_component_lock
import sync_website as sync


class ComponentSyncTest(unittest.TestCase):
    def setUp(self):
        self.base=sync.ROOT/'.gallery-dev/tests'/uuid.uuid4().hex
        self.source=self.base/'component';self.site=self.base/'website'
        names=['gallery-component.json','layouts/gallery.html','assets/js/gallery.js',
            'data/gallery/public.json','data/gallery/allowlist.json','data/gallery/media.json',
            'scripts/check_gallery_component.py','scripts/validate_public_gallery.py',
            'scripts/public_gallery_schema.py','scripts/public_gallery_media.py']
        for directory in (self.source,self.site):
            directory.mkdir(parents=True)
            self.git(directory,'init','-b','main');self.git(directory,'config','user.name','Component fixture')
            self.git(directory,'config','user.email','fixture@example.invalid')
            (directory/'.gitignore').write_text('/.gallery-local/\n__pycache__/\n')
        descriptor=dict(schema_version=1,repository=sync.REPOSITORY,files=names)
        for name in names:
            if name.startswith('scripts/'):content=(sync.ROOT/name).read_bytes()
            elif name=='gallery-component.json':content=sync.encoded(descriptor)
            elif name=='data/gallery/public.json':content=sync.encoded(dict(schema_version=1,records=[]))
            elif name=='data/gallery/allowlist.json':content=sync.encoded(dict(schema_version=1,image_hosts=['chutj.github.io'],approved_records=[]))
            elif name=='data/gallery/media.json':content=sync.encoded(dict(schema_version=1,files=[]))
            else:content=b'fixture content\n'
            for directory in (self.source,self.site):sync.write(directory/name,content)
        sync.write(self.site/'unrelated.txt',b'preserve unrelated website content')
        provenance=dict(initial_site_files={n:content_hash((self.site/n).read_bytes(),n) for n in names})
        sync.write(self.source/'PROVENANCE.json',sync.encoded(provenance))
        for directory in (self.source,self.site):self.commit(directory)

    def git(self,root,*args):
        return subprocess.check_output(['git',*args],cwd=root,stderr=subprocess.DEVNULL).decode().strip()

    def commit(self,root):
        self.git(root,'add','.');self.git(root,'commit','-m','Isolated component fixture')

    def test_pin_idempotence_and_drift_block(self):
        result=sync.apply(self.site,self.source)
        self.assertTrue(result['applied']);self.assertEqual(validate_component_lock(self.site)['commit'],self.git(self.source,'rev-parse','HEAD'))
        self.assertFalse(sync.apply(self.site,self.source)['applied'])
        target=self.site/'assets/js/gallery.js';target.write_bytes(b'manual website edit')
        with self.assertRaisesRegex(ValueError,'outside its pinned'):
            sync.apply(self.site,self.source)
        self.assertEqual(target.read_bytes(),b'manual website edit')

    def test_explicit_old_version_and_reviewed_update(self):
        sync.apply(self.site,self.source);old=self.git(self.source,'rev-parse','HEAD')
        (self.source/'assets/js/gallery.js').write_bytes(b'reviewed upstream update\n');self.commit(self.source)
        self.assertEqual(sync.plan(self.site,self.source,old)[0]['changes'],[])
        updated=sync.apply(self.site,self.source)
        self.assertEqual((self.site/'assets/js/gallery.js').read_bytes().replace(b'\r\n',b'\n'),b'reviewed upstream update\n')
        self.assertEqual((self.site/'unrelated.txt').read_bytes(),b'preserve unrelated website content')
        self.assertIn('assets/js/gallery.js',updated['changes'])

    def test_bootstrap_does_not_overwrite_existing_edits(self):
        (self.site/'assets/js/gallery.js').write_bytes(b'unreviewed local work')
        with self.assertRaisesRegex(ValueError,'differs from reviewed'):
            sync.apply(self.site,self.source)
        self.assertEqual((self.site/'assets/js/gallery.js').read_bytes(),b'unreviewed local work')

    def test_manifest_cannot_export_private_paths(self):
        path=self.source/'gallery-component.json';data=sync.read(path);data['files'].append('../private.pdf')
        sync.write(path,sync.encoded(data));self.commit(self.source)
        with self.assertRaises(ValueError):sync.plan(self.site,self.source)

    def test_capture_requires_review_and_never_copies_other_material(self):
        sync.write(self.site/'private-note.md',b'not part of the public bundle')
        with self.assertRaisesRegex(ValueError,'reviewed'):
            sync.capture_public(self.site,False,self.source)
        self.assertEqual(sync.capture_public(self.site,True,self.source)['public_figures'],0)
        self.assertFalse((self.source/'private-note.md').exists())

    def test_uncommitted_component_changes_are_rejected(self):
        (self.source/'assets/js/gallery.js').write_bytes(b'uncommitted version')
        with self.assertRaisesRegex(ValueError,'Commit/review'):
            sync.plan(self.site,self.source)
