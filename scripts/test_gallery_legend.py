"""Synthetic public-gate fixtures for separately displayed shared legends."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
import uuid
from public_gallery_schema import APPROVAL_FIELDS, metadata_hash, validate_dataset
from public_gallery_media import validate_media


class SharedLegendTest(unittest.TestCase):
    def setUp(self):
        self.root=Path(__file__).resolve().parents[1]/'.gallery-local/legend-tests'/uuid.uuid4().hex
        self.root.mkdir(parents=True)
        self.original=b'synthetic original image';self.shared=b'synthetic source legend'
        image_hash=hashlib.sha256(self.original).hexdigest();legend_hash=hashlib.sha256(self.shared).hexdigest()
        base='https://chutj.github.io/figures/approved/'+image_hash+'/'
        self.record=dict(id='synthetic-map-panel',title='Synthetic map panel',primary='Maps',categories=['Maps'],journal='Fixture Journal',year=2020,
            doi='10.1234/fixture',figure='Figure 1a',paper='Synthetic test paper',author='Fixture Author',source='https://doi.org/10.1234/fixture',
            sections={key:'Synthetic reference notes.' for key in ('What the figure shows','Statistics & symbols','Color & encoding','Design lessons','Verification & limitations')},
            translation_status='reviewed',width=1,height=1,source_image_sha256=image_hash,image=base+'figure.png',thumbnail=base+'figure.png',srcset='',
            rights=dict(status='approved',public_use_allowed=True,human_reviewed=True,approved_by='Fixture reviewer',approved_at='2020-01-01',permission_basis='license',
                license='CC BY 4.0',license_url='https://creativecommons.org/licenses/by/4.0/',evidence_reference='fixture-evidence',attribution='Fixture Author, synthetic paper.',
                review_evidence_sha256='0'*64,modification_status='Unchanged synthetic excerpt.',additional_credit='Synthetic fixture only.'),
            legend=dict(image=base+'legend.png',sha256=legend_hash,width=1,height=1,label='Original shared legend'))
        self.pin()
        media=[]
        for url,content in [(self.record['image'],self.original),(self.record['legend']['image'],self.shared)]:
            name='static/'+url.split('chutj.github.io/',1)[1];path=self.root/name
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
            media.append(dict(id=self.record['id'],url=url,sha256=hashlib.sha256(content).hexdigest()))
        self.manifest=dict(schema_version=1,files=media)
        (self.root/'data/gallery').mkdir(parents=True)
        self.save_manifest()

    def pin(self):
        self.record['metadata_sha256']=metadata_hash(self.record)
        self.dataset=dict(schema_version=1,records=[self.record])
        self.policy=dict(schema_version=1,image_hosts=['chutj.github.io'],approved_records=[{k:copy.deepcopy(self.record[k]) for k in APPROVAL_FIELDS}])

    def save_manifest(self):
        (self.root/'data/gallery/media.json').write_text(json.dumps(self.manifest),encoding='utf-8')

    def test_legend_is_separate_media_and_does_not_widen_categories(self):
        self.assertEqual(validate_dataset(self.dataset,self.policy),1)
        self.assertEqual(len(validate_media(self.root,self.dataset,self.policy)),2)
        self.assertEqual(self.record['categories'],['Maps'])

    def test_legend_metadata_change_requires_a_new_approval(self):
        self.record['legend']['label']='Changed source legend'
        with self.assertRaisesRegex(ValueError,'metadata changed'):
            validate_dataset(self.dataset,self.policy)

    def test_private_legend_url_is_rejected_even_after_repinning(self):
        self.record['legend']['image']='https://127.0.0.1/private.png';self.pin()
        with self.assertRaises(ValueError):validate_dataset(self.dataset,self.policy)

    def test_legend_bytes_must_match_reviewed_metadata_not_only_manifest(self):
        item=self.manifest['files'][1];path=self.root/('static/'+item['url'].split('chutj.github.io/',1)[1])
        path.write_bytes(b'changed shared legend');item['sha256']=hashlib.sha256(path.read_bytes()).hexdigest();self.save_manifest()
        with self.assertRaisesRegex(ValueError,'Shared legend differs'):
            validate_media(self.root,self.dataset,self.policy)

    def test_missing_legend_manifest_entry_is_rejected(self):
        self.manifest['files'].pop();self.save_manifest()
        with self.assertRaisesRegex(ValueError,'Missing exact media'):
            validate_media(self.root,self.dataset,self.policy)

    def test_legacy_record_remains_valid_without_optional_legend(self):
        del self.record['legend'];self.pin()
        self.assertEqual(validate_dataset(self.dataset,self.policy),1)
