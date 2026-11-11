"""Real Hugo tests for lazy public payloads; synthetic data only, no FIG reads."""
import copy
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from urllib.parse import urlparse

from public_gallery_schema import metadata_hash


ROOT = Path(__file__).resolve().parents[1]


def fixture():
    """Self-contained synthetic policy object, usable in either public repository."""
    record = dict(id='policy-fixture', title='Synthetic policy fixture',
        primary='Policy test', categories=['Policy test'], journal='Test fixture', year=2026,
        doi='10.1234/policy-fixture', figure='Fixture', paper='Synthetic policy contract test',
        author='Test fixture', source='https://doi.org/10.1234/policy-fixture',
        sections={key: 'Synthetic policy test text.' for key in
                  ('What the figure shows', 'Statistics & symbols', 'Color & encoding',
                   'Design lessons', 'Verification & limitations')},
        translation_status='reviewed', width=800, height=600)
    rights = dict(status='approved', public_use_allowed=True, human_reviewed=True,
        approved_by='policy-test-only', approved_at='2020-01-01', permission_basis='license',
        license='Synthetic test permission', license_url='https://example.org/policy',
        evidence_reference='TEST-NOT-A-REAL-PERMISSION', attribution='Synthetic fixture only',
        review_evidence_sha256='b'*64, modification_status='Synthetic fixture; no actual image.',
        additional_credit='Synthetic test fixture only.')
    approval = dict(id=record['id'], source_image_sha256='a'*64,
        metadata_sha256=metadata_hash(record), rights=rights,
        image='https://cdn.example.org/fixture.png',
        thumbnail='https://cdn.example.org/fixture-thumb.webp',
        srcset='https://cdn.example.org/fixture-small.webp 320w, https://cdn.example.org/fixture-thumb.webp 640w')
    record.update({key: value for key, value in approval.items() if key != 'id'})
    return record, dict(schema_version=1, image_hosts=['cdn.example.org'],
                        approved_records=[approval])


class GalleryDataParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inside = False
        self.chunks = []
        self.search_url = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'script' and attrs.get('id') == 'gallery-data':
            self.inside = True
            self.search_url = attrs.get('data-search-url')

    def handle_endtag(self, tag):
        if tag == 'script':
            self.inside = False

    def handle_data(self, data):
        if self.inside:
            self.chunks.append(data)


@unittest.skipUnless(shutil.which('hugo'), 'Hugo is required for real payload rendering')
class GalleryPayloadTest(unittest.TestCase):
    def setUp(self):
        parent = ROOT / '.gallery-local/payload-tests'
        parent.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ('layouts/_default', 'layouts/_partials/gallery', 'assets/js',
                     'assets/css', 'content/gallery', 'data/gallery', '.gallery-local'):
            (self.root / name).mkdir(parents=True, exist_ok=True)
        for name in ('layouts/gallery.html', 'layouts/_partials/gallery/public-records.html',
                     'layouts/_partials/gallery/licensing.html', 'assets/js/gallery-tools.js',
                     'assets/js/gallery.js', 'assets/css/gallery.css'):
            shutil.copyfile(ROOT / name, self.root / name)
        self.write_text('layouts/_default/baseof.html',
                        '<!doctype html><html><body>{{ block "main" . }}{{ end }}</body></html>')
        self.write_text('layouts/_default/list.html', '{{ define "main" }}{{ .Title }}{{ end }}')
        self.write_text('layouts/_partials/svg.html', '<svg aria-hidden="true"></svg>')
        self.write_text('content/gallery/_index.md', '---\ntitle: Figure Gallery\nlayout: gallery\n---\n')
        self.write_text('hugo.toml', "baseURL = 'https://chutj.github.io/'\n[params]\ngalleryLocalPreview = true\n")
        self.record, self.policy = fixture()
        self.record.update(title='Synthetic map overview', paper='Synthetic drought research',
                           author='Example Author', primary='Maps', categories=['Maps', 'Model evaluation'],
                           figure='Fig. 2 a–b')
        self.record['sections'].update({
            'What the figure shows': 'Synthetic regional drought response.',
            'Statistics & symbols': 'Synthetic Monte Carlo uncertainty.',
            'Color & encoding': 'Synthetic diverging blue and orange #ABCDEF.',
            'Design lessons': 'Synthetic aligned panels.',
            'Verification & limitations': 'PRIVATE-HIDDEN-SECTION-SENTINEL',
        })
        self.record['rights']['attribution'] = 'ATTRIBUTION-LAZY-ONLY-SENTINEL'
        self.record['internal_review'] = 'PRIVATE-REVIEW-FIELD-SENTINEL'
        self.repin()
        self.write_json('.gallery-local/catalog.json', {'records': [
            {'id': 'private-only', 'title': 'PRIVATE-CATALOG-SENTINEL',
             'asset': 'C:/Users/Private/private.png'}]})
        self.build_number = 0

    def write_text(self, name, text):
        (self.root / name).write_text(text, encoding='utf-8')

    def write_json(self, name, value):
        self.write_text(name, json.dumps(value, ensure_ascii=False))

    def repin(self):
        self.record['metadata_sha256'] = metadata_hash(self.record)
        self.policy['approved_records'][0].update({key: copy.deepcopy(self.record[key])
            for key in ('metadata_sha256', 'rights')})

    def build(self, records=None):
        records = [self.record] if records is None else records
        self.write_json('data/gallery/public.json', {'schema_version': 1, 'records': records})
        self.write_json('data/gallery/allowlist.json', self.policy)
        self.build_number += 1
        output = self.root / ('out-' + str(self.build_number))
        result = subprocess.run([shutil.which('hugo'), 'build', '--environment', 'production',
                                 '--destination', str(output), '--noBuildLock'],
                                cwd=self.root, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn('WARN', result.stdout + result.stderr)
        html = (output / 'gallery/index.html').read_text(encoding='utf-8')
        parser = GalleryDataParser()
        parser.feed(html)
        self.search_url = parser.search_url
        cards = json.loads(''.join(parser.chunks)) if parser.chunks else []
        return output, html, cards

    def endpoint(self, output, card):
        return self.read_json_asset(output, card['details_url'])

    def read_json_asset(self, output, url):
        self.assertTrue(url)
        parsed = urlparse(url)
        self.assertIn(parsed.netloc, ('', 'chutj.github.io'))
        self.assertFalse(parsed.query or parsed.fragment)
        path = output / parsed.path.lstrip('/')
        self.assertTrue(path.is_file())
        self.assertEqual(path.stem, hashlib.sha256(path.read_bytes()).hexdigest())
        return path, json.loads(path.read_text(encoding='utf-8'))

    def test_compact_index_and_named_full_payload_do_not_copy_private_fields(self):
        output, html, cards = self.build()
        self.assertEqual(len(cards), 1)
        card = cards[0]
        for field in ('sections', 'rights', 'image', 'internal_review', 'pdf_reference', 'search_fields'):
            self.assertNotIn(field, card)
        self.assertEqual(card['doi'], self.record['doi'])
        self.assertNotIn('synthetic monte carlo uncertainty', html.lower())
        self.assertNotIn('ATTRIBUTION-LAZY-ONLY-SENTINEL', html)
        self.assertNotIn('PRIVATE-REVIEW-FIELD-SENTINEL', html)
        _, detail = self.endpoint(output, card)
        self.assertEqual(detail['id'], card['id'])
        self.assertEqual(detail['image'], self.record['image'])
        self.assertEqual(detail['rights'], self.record['rights'])
        self.assertEqual(detail['sections'], self.record['sections'])
        self.assertNotIn('internal_review', detail)
        _, search_rows = self.read_json_asset(output, self.search_url)
        self.assertEqual([row['id'] for row in search_rows], [card['id']])
        self.assertIn('#abcdef', search_rows[0]['color'])
        search_text = json.dumps(search_rows).lower()
        for sentinel in ('private-hidden-section-sentinel', 'private-review-field-sentinel',
                         'attribution-lazy-only-sentinel'):
            self.assertNotIn(sentinel, search_text)
        for path in output.rglob('*'):
            if path.is_file() and path.suffix in ('.html', '.json'):
                self.assertNotIn('PRIVATE-CATALOG-SENTINEL', path.read_text(encoding='utf-8'))

    def test_unapproved_or_changed_record_cannot_generate_a_detail_endpoint(self):
        for kind in ('no-approval', 'changed-metadata', 'changed-rights'):
            bad = copy.deepcopy(self.record)
            if kind == 'no-approval':
                self.policy['approved_records'] = []
            elif kind == 'changed-metadata':
                _, self.policy = fixture()
                self.repin()
                bad['title'] = 'Not reapproved after modification'
            else:
                bad['rights']['status'] = 'unverified'
            with self.subTest(kind=kind):
                output, html, cards = self.build([bad])
                self.assertEqual(cards, [])
                self.assertIsNone(self.search_url)
                self.assertIn('No public figures available', html)
                self.assertFalse(list((output / 'gallery/records').rglob('*.json')))
                self.assertFalse(list((output / 'gallery/search').glob('*.json')))

    def test_reapproved_description_gets_a_new_content_addressed_url(self):
        output, _, cards = self.build()
        old_url = cards[0]['details_url']
        self.endpoint(output, cards[0])
        self.record['sections']['Design lessons'] = 'New synthetic design lesson after review.'
        self.repin()
        output, _, cards = self.build()
        self.assertNotEqual(cards[0]['details_url'], old_url)
        _, detail = self.endpoint(output, cards[0])
        self.assertEqual(detail['sections']['Design lessons'], self.record['sections']['Design lessons'])

    @unittest.skipUnless(shutil.which('node'), 'Node is needed for full-library search parity')
    def test_compact_search_matches_full_record_for_all_existing_fields(self):
        output, _, cards = self.build()
        _, search_rows = self.read_json_asset(output, self.search_url)
        script = r'''const assert=require('node:assert/strict');
const tools=require(process.argv[1]);
let s='';process.stdin.on('data',c=>s+=c);process.stdin.on('end',()=>{
const {full,card,searchRows}=JSON.parse(s);
assert.throws(() => tools.expandSearchIndex([card], [{...searchRows[0], id:'wrong-figure'}]));
[card.search_fields] = tools.expandSearchIndex([card], searchRows);
for(const [query,category,advanced,focus] of [
 ['regional drought','',{},''],['Monte Carlo','',{},''],['#ABCDEF','',{},''],
 ['synthetic drought research','',{},''],['missing','',{},''],
 ['', 'Maps', {author:'Example Author',journal:'fixture'}, 'Model evaluation'],
 ['', '', {year:'2020–2026',doi:'10.1234',figure:'Figure 2a'}, ''],
 ['', '', {method:'aligned panels',color:'blue orange'}, ''],
 ['', '', {method:'PRIVATE-HIDDEN-SECTION-SENTINEL'}, '']]){
 assert.equal(tools.matches(card,query,category,advanced,focus),
              tools.matches(full,query,category,advanced,focus),JSON.stringify({query,advanced}));
}
});'''
        result = subprocess.run(['node', '-e', script, str(ROOT / 'assets/js/gallery-tools.js')],
                                input=json.dumps({'full': self.record, 'card': cards[0], 'searchRows': search_rows}),
                                capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
