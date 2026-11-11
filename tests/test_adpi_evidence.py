import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bsa.adpi_review import run,settings_inputs
from bsa.adpi_screen import screen
from bsa.cli import digest

ROOT=Path(__file__).resolve().parents[1]


class ADPIFactEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.source=self.root/'criterion.txt';self.source.write_text('Synthetic criterion source')
        self.extra=self.root/'product.txt';self.extra.write_text('Synthetic product review source')
        self.settings=self.root/'settings.json'
        self.spec=dict(criterion=dict(source='Synthetic criterion',room_load_range_W_m2=[35,160],ratio_range=[1,3.4]),
            room_load_W_m2=None,facts={k:None for k in ('room_load_verified','product_category_verified','lengths_verified','installation_verified','edition_selected')},
            source=self.source.name,source_sha256=digest(self.source),
            fact_evidence=dict(product_category_verified=[dict(source=self.extra.name,sha256=digest(self.extra),locator='Synthetic section',note='Byte binding only;no physical category assertion')]))
        self.save()
        self.workflow=self.root/'workflow';(self.workflow/'lookup').mkdir(parents=True)
        (self.workflow/'workflow.json').write_text(json.dumps(dict(tasks=dict(lookup=dict(kind='terminal_throw',status='pass')))))
        lookup=dict(terminals=[dict(id='T',directions=dict(east=dict(cases={k:dict(ratio=2.,status='within_catalogue') for k in ('maximum','minimum')})))])
        (self.workflow/'lookup/terminal-results.json').write_text(json.dumps(lookup))

    def save(self):self.settings.write_text(json.dumps(self.spec))

    def test_fact_documents_pinned_without_promoting_unknown_or_legacy_facts(self):
        _,pins=settings_inputs(self.settings)
        self.assertEqual(pins[str(self.extra)],digest(self.extra))
        # Fake workflow integrity isolates postprocessor evidence plumbing;not
        # native CAD,product applicability or engineering acceptance evidence.
        with patch('bsa.adpi_review.verify',return_value=dict(integrity_pass=True)):
            result=run(self.workflow,self.settings,self.root/'review.json')
        self.assertIsNone(result['facts']['product_category_verified'])
        self.assertEqual(result['applicability'],'pending');self.assertFalse(result['ADPI_verified'])
        self.assertIn(str(self.extra),result['inputs'])
        self.spec.pop('fact_evidence');self.save()
        self.assertNotIn(str(self.extra),settings_inputs(self.settings)[1])

    def test_changed_source_invalid_mapping_and_source_overwrite_reject(self):
        original=copy.deepcopy(self.spec)
        for case in ('hash','unknown_fact','missing_note','absolute_source'):
            self.spec=copy.deepcopy(original)
            record=self.spec['fact_evidence']['product_category_verified'][0]
            if case=='hash':record['sha256']='0'*64
            elif case=='unknown_fact':self.spec['fact_evidence']['unknown']=self.spec['fact_evidence'].pop('product_category_verified')
            elif case=='missing_note':record.pop('note')
            else:record['source']=str(self.extra)
            self.save()
            with self.subTest(case=case),self.assertRaises(ValueError):settings_inputs(self.settings)
        self.spec=original;self.save()
        before=self.extra.read_bytes()
        with self.assertRaises(ValueError):
            run(self.workflow,self.settings,self.extra)
        self.assertEqual(self.extra.read_bytes(),before)

    def test_evidence_mutation_during_screen_keeps_output_absent(self):
        def changed(*args,**kwargs):
            result=screen(*args,**kwargs);self.extra.write_text('Changed during screening');return result
        output=self.root/'mutated.json'
        with patch('bsa.adpi_review.verify',return_value=dict(integrity_pass=True)),patch('bsa.adpi_review.screen',side_effect=changed):
            with self.assertRaisesRegex(ValueError,'changed during'):run(self.workflow,self.settings,output)
        self.assertFalse(output.exists())
