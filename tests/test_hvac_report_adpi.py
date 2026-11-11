import copy
import json
from unittest import TestCase

from bsa.adpi_review import run as review
from bsa.cli import digest
from bsa.hvac_report import run
from tests import test_allocation_lookup as fixtures


class HVACReportADPITests(TestCase):
    def setUp(self):
        fixture=fixtures.AllocationLookupTests();fixture.setUp();self.addCleanup(fixture.temp.cleanup)
        self.root=fixture.root
        duct=dict(basis='Synthetic assumptions',air=dict(density_kg_m3=1.2,viscosity_Pa_s=1.81e-5,roughness_m=.00009),
            tree=dict(root='R',sections=[dict(id='SA',**{'from':'R','to':'A'}),dict(id='SB',**{'from':'R','to':'B'})],leaf_terminals=dict(A=['A'],B=['B']),basis='Synthetic'),
            sections=[dict(id=k,width_m=.8,height_m=.4,limits=dict(actual_velocity_m_s=8,friction_Pa_m=2,aspect_ratio=4)) for k in ('SA','SB')])
        (self.root/'ducts.json').write_text(json.dumps(duct))
        fixture.plan['tasks'].append(dict(id='ducts',kind='duct_schedule',project='ducts.json',depends_on='allocation'))
        fixture.plan['requirements'].append(dict(fixture.plan['requirements'][0],id='RD',task='ducts'))
        fixture.run_plan('workflow');self.workflow=self.root/'workflow'
        self.source=self.root/'criterion.txt';self.source.write_text('Synthetic criterion')
        self.extra=self.root/'product.txt';self.extra.write_text('Synthetic category source')
        settings=dict(criterion=dict(source='Synthetic criterion',room_load_range_W_m2=[35,160],ratio_range=[1,3.4]),room_load_W_m2=None,
            facts=dict(room_load_verified=None,product_category_verified=True,lengths_verified=None,installation_verified=None,edition_selected=True),
            source=self.source.name,source_sha256=digest(self.source),fact_evidence=dict(product_category_verified=[
                dict(source=self.extra.name,sha256=digest(self.extra),locator='Synthetic section',note='Scoped observation <script>untrusted()</script> & source')]))
        self.settings=self.root/'settings.json';self.settings.write_text(json.dumps(settings))
        self.review=self.root/'adpi.json';review(self.workflow,self.settings,self.review)

    def test_source_reconstructed_summary_preserves_unknowns_and_escaped_notes(self):
        result=run(self.workflow,self.root/'report',adpi_review=self.review)
        content=(self.root/'report/HVAC System Design.html').read_text()
        self.assertIn('ADPI applicability and evidence',content)
        self.assertIn('Applicability: pending',content)
        self.assertIn('not_evaluated=4',content)
        self.assertIn('Room sensible load: Unverified',content)
        self.assertIn('Product category within selected criterion: Declared supported',content)
        self.assertIn('&lt;script&gt;untrusted()&lt;/script&gt; &amp; source',content)
        self.assertNotIn('<script>',content)
        self.assertIn(str(self.extra),result['inputs'])
        self.assertTrue(result['adpi_review_summary']);self.assertFalse(result['design_accepted'])

    def test_forged_screen_settings_identity_and_source_changes_reject(self):
        original=json.loads(self.review.read_text())
        for case in ('ADPI_verified','applicability','all_ratios_within_scope','settings_path','inputs'):
            record=copy.deepcopy(original)
            if case=='settings_path':record.pop('settings_path')
            elif case=='inputs':record['inputs'].pop(str(self.extra))
            else:record[case]='eligible' if case=='applicability' else True
            self.review.write_text(json.dumps(record));output=self.root/('bad-'+case)
            with self.subTest(case=case),self.assertRaises(ValueError):run(self.workflow,output,adpi_review=self.review)
            self.assertFalse(output.exists())
        self.review.write_text(json.dumps(original));self.extra.write_text('Changed evidence')
        with self.assertRaisesRegex(ValueError,'hash mismatch'):
            run(self.workflow,self.root/'changed-source',adpi_review=self.review)

    def test_pdf_checks_every_adpi_summary_paragraph_and_rejects_omission(self):
        import reportlab
        from pathlib import Path
        from bsa.hvac_report_pdf import run as render
        directory=self.root/'report';report=run(self.workflow,directory,adpi_review=self.review)
        font=Path(reportlab.__file__).parent/'fonts/Vera.ttf'
        result=render(directory,self.root/'pdf',font)
        self.assertEqual(result['adpi_review_paragraphs_checked'],len(report['adpi_review_summary']))
        self.assertGreater(result['adpi_review_paragraphs_checked'],5)
        self.assertFalse(result['design_accepted'])
        source=directory/'HVAC System Design.html'
        paragraph=report['adpi_review_summary'][0]
        source.write_text(source.read_text().replace('<p>'+paragraph+'</p>','',1))
        report['html_sha256']=digest(source);(directory/'report.json').write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError,'ADPI review summary differs'):
            render(directory,self.root/'omitted',font)
        self.assertFalse((self.root/'omitted').exists())

    def test_nested_sources_remain_checked_after_report_preparation(self):
        from bsa.hvac_report_pdf import verify_report_inputs
        report=run(self.workflow,self.root/'report',adpi_review=self.review)
        verify_report_inputs(report)
        self.extra.write_text('Evidence changed after report preparation')
        with self.assertRaisesRegex(ValueError,'Report source evidence changed'):verify_report_inputs(report)
